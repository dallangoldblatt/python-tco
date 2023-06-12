import inspect
import re


class _TcoState:
    tco_functions = set()


class _TailCall(Exception):
    """
    Custom exception for identifying tail recursive calls and their arguments
    """
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs


def _rewrite_def(line):
    """
    Rewrite function signature to accept `_tco_handled` kwarg

    :param line: function signature, e.g. 'def f(x, a=True)'
    :return: updated signature, e.g. 'def f(x, a=True, _tco_handled=False)'
    """
    return line[:line.index(')')] + ', _tco_handled=False):\n'


def _rewrite_return(line):
    """
    Rewrite return statement to raise `_TailCall` for tail recursive function calls. Return statements that
    do not contain a function call will not be changed.

    :param line: return statement e.g. `return f(x, a=True)`
    :return: updated return, e.g. `raise _TCO_Call(f, x, a=True)`
    """
    match = re.compile(r'([a-zA-Z0-9_]*)\((.*)\)').search(line)
    if not match:
        return line
    return line[:line.index('return ')] + 'raise _TailCall(' + match.group(1) + ', ' + match.group(2) + ')\n'


def _rewrite_func(func):
    """
    Rewrite source code for `func` to communicate with the TCO decorator's logic

    :param func: tail recursive function
    :return: source code for optimized function
    """
    source = inspect.getsourcelines(func)
    new_source = ''
    whitespace_end = source[0][0].index('@tco')
    for line in source[0][1:]:
        # remove indent from all lines
        line = line[whitespace_end:]
        if line.strip()[:4] == 'def ':
            # function signature needs to accept `_tco_handled` kwarg
            new_source += _rewrite_def(line)
        elif line.strip()[:7] == 'return ':
            # return statement needs to raise `_TailCall` for tail recursive function calls
            new_source += _rewrite_return(line)
        else:
            # remaining lines are not modified
            new_source += line
    return new_source


def tco(*_, **context):
    tco_functions = _TcoState.tco_functions

    def outer(func):
        """
        Decorator to optimize functions containing tail recursive calls.

        :param func: tail recursive function
        :return: optimized function
        """
        # rewrite function code
        new_source = _rewrite_func(func)
        code_obj = compile(new_source, '<string>', 'exec')
        exec(code_obj, globals())
        new_func = globals()[func.__name__]

        # remember which functions have been optimized
        tco_functions.add(new_func)

        # @functools.wraps(func)
        def inner(*args, _tco_handled=False, **kwargs):
            new_func.__globals__.update(context)
            if _tco_handled:
                # inside recursive call, do not enter new trampolene
                return new_func(*args, _tco_handled=True, **kwargs)
            call_func = new_func
            while True:
                try:
                    if call_func in tco_functions:
                        return call_func(*args, _tco_handled=True, **kwargs)
                    else:
                        return call_func(*args, **kwargs)
                except _TailCall as e:
                    # recurive call in func detected, call in next iteration
                    call_func, args, kwargs = e.func, e.args, e.kwargs
        return inner

    tco_functions.add(outer)
    return outer

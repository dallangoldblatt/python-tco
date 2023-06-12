import sys
from unittest import TestCase

from tco import tco


class TestTco(TestCase):

    def setUp(self):
        self.recursion_limit = sys.getrecursionlimit()

    def test_tco(self):
        def factorial(n, acc):
            if n <= 1:
                return acc
            return factorial(n - 1, n * acc)

        @tco()
        def factorial_tco(n, acc):
            if n <= 1:
                return acc
            return factorial_tco(n - 1, n * acc)

        # check validity of factorial functions
        self.assertEqual(factorial(10, 1), 3628800)
        self.assertEqual(factorial(10, 1), factorial_tco(10, 1))

        # check that @tco prevents a RecursionError
        with self.assertRaises(RecursionError):
            factorial(self.recursion_limit + 1, 1)
        self.assertIsInstance(factorial_tco(self.recursion_limit + 1, 1), int)

    def test_tco_context(self):
        """
        Test that helper functions can be added to the context of optimized functions
        """
        def add(lis):
            return sum(lis)

        @tco(add=add)
        def a(n, lis):
            if n <= 1:
                return add(lis)
            return a(n - 1, lis)

        self.assertEqual(a(self.recursion_limit + 1, [1, 2, 3]), 6)

    def test_tco_cyclic(self):
        """
        Test that recurive calls to other optimized functions are optimized
        """
        @tco()
        def a(n):
            if n <= 1:
                return 1
            return b(n - 1)

        @tco()
        def b(n):
            if n <= 1:
                return 1
            return c(n - 1)

        @tco()
        def c(n):
            if n <= 1:
                return 1
            return a(n - 1)

        # since all three functions are optimized, the first call's trampolene should handle recusive calls
        self.assertEqual(a(self.recursion_limit + 1), 1)
        self.assertEqual(b(self.recursion_limit + 1), 1)
        self.assertEqual(c(self.recursion_limit + 1), 1)

    def test_tco_cyclic_fail(self):
        """
        Test that recursive calls to non-optimized recursive functions are not optimized
        """
        def b(n):
            if n <= 1:
                return 1
            return a(n - 1)

        @tco(b=b)
        def a(n):
            if n <= 1:
                return 1
            return b(n - 1)

        # since b is not optimized, each call from a will add a frame to the stack
        with self.assertRaises(RecursionError):
            a(self.recursion_limit + 1)

    def test_tco_inner(self):
        """
        Test that inner functions can be optimized
        """
        def go():
            @tco()
            def a(n):
                if n <= 1:
                    return 1
                return a(n - 1)
            return a(self.recursion_limit + 1)

        self.assertEqual(go(), 1)
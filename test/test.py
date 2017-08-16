#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for PPP package."""
import doctest
import unittest
from argparse import ArgumentParser
import os


SRC_PKG_NAME, TEST_PKG_NAME = 'pma_api', 'test'
PKG_NAMES = [SRC_PKG_NAME, TEST_PKG_NAME]
TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + '/'


class PlaceholderTestClass(unittest.TestCase):
    """Unit tests for the Resource class."""

    def test_init(self):
        """Test initialization."""
        pass


if __name__ == '__main__':
    def get_args():
        """CLI for test runner."""
        desc = 'Run tests for package.'
        parser = ArgumentParser(description=desc)
        doctests_only_help = 'Specifies whether to run doctests only, as ' \
                             'opposed to doctests with unittests. Default is' \
                             ' False.'
        parser.add_argument('-d', '--doctests-only', action='store_true',
                            help=doctests_only_help)
        args = parser.parse_args()
        return args

    def get_test_modules(test_package):
        """Get files to test.

        Args:
            test_package (str): The package containing modules to test.

        Returns:
            list: List of all python modules in package.

        """
        # TODO: Make dynamic. Maybe make TEST_PACKAGES a dict (mod name + path)
        if test_package == SRC_PKG_NAME:
            root_dir = TEST_DIR+'../'+SRC_PKG_NAME
        elif test_package == TEST_DIR:
            root_dir = TEST_DIR
        else:
            raise Exception('Test package not found.')

        test_modules = []
        for dummy, dummy, filenames in os.walk(root_dir):
            for file in filenames:
                if file.endswith('.py'):
                    file = file[:-3]
                    test_module = test_package + '.' + file
                    test_modules.append(test_module)
        return test_modules

    def get_test_suite(test_packages):
        """Get suite to test.

        Args:
            test_packages (list): List of strings of package names.

        Returns:
            TestSuite: Suite to test.
        """
        suite = unittest.TestSuite()
        for package in test_packages:
            pkg_modules = get_test_modules(test_package=package)
            for pkg_module in pkg_modules:
                suite.addTest(doctest.DocTestSuite(pkg_module))
        return suite

    PARAMS = get_args()
    TEST_SUITE = get_test_suite(PKG_NAMES)
    unittest.TextTestRunner(verbosity=1).run(TEST_SUITE)
    if PARAMS.doctests_only:  # TODO: For dev testing needs. Refactor.
        pass
        # TEST_SUITE = get_test_suite()
        # unittest.TextTestRunner(verbosity=1).run(TEST_SUITE)
    else:
        # unittest.main()
        pass

"""Init for Doctest Unittest Runner."""
import os
import unittest
import doctest
from argparse import ArgumentParser

from .definitions.error import DoctestUnittestRunnerException


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


def get_test_modules(pkg_name, test_dir, relative_path_to_root):
    """Get files to test.

    Args:
        pkg_name (str): Package name.
        test_dir (str): Path to test directory.
        relative_path_to_root (str): Relative path to root directory of app
            from test directory.

    Returns:
        list: List of all python modules in package.

    """
    test_dir_name = os.path.basename(os.path.dirname(test_dir))

    try:
        pkg_root_dir = test_dir if pkg_name == test_dir_name \
            else test_dir + relative_path_to_root + pkg_name
    except:
        msg = ' Test package \'{}\' not found.'.format(pkg_name)
        raise DoctestUnittestRunnerException(msg)

    test_modules = []
    for dummy, dummy, filenames in os.walk(pkg_root_dir):
        for file in filenames:
            if file.endswith('.py'):
                file = file[:-3]
                test_module = pkg_name + '.' + file
                test_modules.append(test_module)
    return test_modules


def get_test_suite(test_dir, relative_path_to_root, package_names):
    """Get suite to test.

    Args:
        test_dir (str): Path to test directory.
        relative_path_to_root (str): Relative path to root directory of app
            from test directory.
        package_names (list): List of strings of package names to test.

    Returns:
        TestSuite: Suite to test.
    """
    suite = unittest.TestSuite()
    for package in package_names:
        pkg_modules = get_test_modules(package, test_dir,
                                       relative_path_to_root)
        for pkg_module in pkg_modules:
            suite.addTest(doctest.DocTestSuite(pkg_module))
    return suite


def doctest_unittest_runner(test_dir, relative_path_to_root, package_names):
    """Perform unittests and doctests or just doctests.

    Args:
        test_dir (str): Path to test directory.
        relative_path_to_root (str): Relative path to root directory of app
            from test directory.
        package_names (list): List of strings of package names to test.
    """
    params = get_args()
    test_suite = get_test_suite(test_dir, relative_path_to_root, package_names)
    unittest.TextTestRunner(verbosity=1).run(test_suite)
    if params.doctests_only:  # TODO: For dev testing needs. Refactor.
        pass
        # TEST_SUITE = get_test_suite()
        # unittest.TextTestRunner(verbosity=1).run(TEST_SUITE)
    else:
        # unittest.main()
        pass

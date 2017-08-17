#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for PPP package."""
import unittest


class TestApiRoutes(unittest.TestCase):
    """Unit tests for the Resource class."""

    def test_get_resources(self):
        """Test initialization."""
        # from pma_api.api_1_0 import get_resources
        pass


if __name__ == '__main__':
    import os
    from test.utils.doctest_unittest_runner import doctest_unittest_runner
    TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + '/'
    doctest_unittest_runner(test_dir=TEST_DIR, relative_path_to_root='../',
                            package_names=['pma_api', 'test'])

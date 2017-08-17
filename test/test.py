#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for PPP package."""
import os
import unittest

from test.utils.doctest_unittest_runner import doctest_unittest_runner


class PlaceholderTestClass(unittest.TestCase):
    """Unit tests for the Resource class."""

    def test_init(self):
        """Test initialization."""
        pass


if __name__ == '__main__':
    test_dir = os.path.dirname(os.path.realpath(__file__)) + '/'
    doctest_unittest_runner(test_dir=test_dir, relative_path_to_root='../',
                            package_names=['pma_api', 'test'])

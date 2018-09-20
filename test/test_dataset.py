#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for dataset class."""
import unittest

from pma_api.models import Dataset


class TestDataset(unittest.TestCase):
    """Test that the dataset class works.

    To run this test directly, issue this command from the root directory:
       python -m test.test_dataset
    """

    def test_dataset(self):
        """Create a new entry in 'dataset' table and read data."""
        # 1. ceate a new Dataset() object
        dataset = Dataset(file_path ='')
        print('hi')

        # 2. write it to DB
        pass

        # 3. check to make sure it is there (assert something)
        self.assertTrue(False)  # temp


if __name__ == '__main__':
    unittest.main(TestDataset())

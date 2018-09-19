#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test dataset"""
import unittest

from pma_api.models.dataset import Dataset

class TestDataset(unittest.TestCase):
     """Test that the dataset class works.

     To run this test directly, issue this command from the root directory:
        python -m test.pma_test
     """

     def test_dataset(self):
        """Test that the dataset class works."""
         # 1. ceate a new Dataset() object
        dataset = Dataset(file_path ='')
        from pdb import set_trace; set_trace()

         # 2. write it to DB

         # 3. check to make sure it is there (assert something)
        self.assertTrue(False)


if __name__ == '__main__':
    test = TestDataset()
    test.test_dataset()

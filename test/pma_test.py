#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests."""
import os
import unittest
from sys import stderr

from sqlalchemy.exc import OperationalError as OperationalError1
from psycopg2 import OperationalError as OperationalError2
from sqlalchemy.util.queue import Empty as EmptyError

from manage import app

from pma_api.models.dataset import Dataset


class TestRoutes(unittest.TestCase):
    """Test routes."""

    ignore_routes = ('/static/<path:filename>',)
    ignore_end_patterns = ('>',)

    def setUp(self):
        """Set up: Put Flask app in test mode."""
        app.testing = True
        self.app = app.test_client()

    @staticmethod
    def valid_route(route):
        """Validate route.

        Args:
            route (str): Route url pattern.

        Returns:
            bool: True if valid, else False.
        """
        if route in TestRoutes.ignore_routes \
                or route.endswith(TestRoutes.ignore_end_patterns):
            return False
        return True

    def test_routes(self):
        """Smoke test routes to ensure no runtime errors.."""
        try:
            routes = [route.rule for route in app.url_map.iter_rules()
                      if self.valid_route(route.rule)]
            for route in routes:
                self.app.get(route)
        except (EmptyError, OperationalError1, OperationalError2) as err:
            message = '\n\nAn error occurred while trying to connect to the ' \
                      'database. Is it running?\n\nOriginal error message:\n'
            template = 'An exception of type {0} occurred. Arguments:\n{1!r}'
            message += template.format(type(err).__name__, err.args)
            print(message, file=stderr)


# class TestDB(unittest.TestCase):  # TODO: Adapt from tutorial.
#     """Test database functionality.
#
#     Tutorial: http://flask.pocoo.org/docs/0.12/testing/
#     """
#
#     def setUp(self):
#         """Set up: (1) Put Flask app in test mode, (2) Create temp DB."""
#         import tempfile
#         from manage import initdb
#         self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
#         app.testing = True
#         self.app = app.test_client()
#         with app.app_context():
#             initdb()
#
#     def tearDown(self):
#         """Tear down: (1) Close temp DB."""
#         os.close(self.db_fd)
#         os.unlink(app.config['DATABASE'])
#
#     def test_empty_db(self):
#         """Test empty database."""
#         resp = self.app.get('/')
#         assert b'No entries here so far' in resp.data


class TestDataset(unittest.TestCase):
     """Test that the dataset class works.

     To run this test directly, issue this command from the root directory:
        python test/pma_test.py TestDataset.test_dataset
     """

     def test_dataset(self):
        """Test that the dataset class works."""
         # 1. ceate a new Dataset() object
        dataset = Dataset(file_path ='')

         # 2. write it to DB
         # 3. check to make sure it is there (assert something)
        self.assertTrue(False)


if __name__ == '__main__':
    from test.utils.doctest_unittest_runner import doctest_unittest_runner
    TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + '/'
    doctest_unittest_runner(test_dir=TEST_DIR, relative_path_to_root='../',
                            package_names=['pma_api', 'test'])

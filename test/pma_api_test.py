#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests."""
import os
import unittest

from sqlalchemy.exc import OperationalError as OperationalError1
from psycopg2 import OperationalError as OperationalError2
from sqlalchemy.util.queue import Empty as EmptyError

from manage import app


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
            # from pdb import set_trace; set_trace()  # DEBUG
            for route in routes:
                self.app.get(route)
        except (EmptyError, OperationalError1, OperationalError2) as err:
            template = 'An exception of type {0} occurred. Arguments:\n{1!r}'
            message = '\n\nAn error occurred while trying to connect to the ' \
                      'database. Frankly, I\'m not sure why, but this test ' \
                      'seems to require that that Postgres be running, rather'\
                      'than just using the local SQLite DB. It also does not' \
                      'appear that the server needs to be running.\n' \
                      ' -jef 2018/09/05' \
                      '\n\nOriginal error message:\n'
            message += template.format(type(err).__name__, err.args)
            raise Exception(message)


if __name__ == '__main__':
    from test import doctest_unittest_runner
    TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + '/'
    doctest_unittest_runner(test_dir=TEST_DIR, relative_path_to_root='../',
                            package_names=['pma_api', 'test'])

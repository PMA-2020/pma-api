#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests.

#to-do's:
- Warning: path/to/site-packages/psycopg2/__init__.py:144: UserWarning: The
psycopg2 wheel package will be renamed from release 2.8; in order to keep
installing from binary please use "pip install psycopg2-binary" instead. For
details see:
<http://initd.org/psycopg/docs/install.html#binary-install-from-pypi>.)
"""
import inspect
import os
import time
import unittest
from glob import glob
from typing import List

from flask import Response
from sqlalchemy.exc import OperationalError

# import xlrd
from pma_api.config import AWS_S3_STORAGE_BUCKETNAME as BUCKET, \
    S3_BACKUPS_DIR_PATH
from test.config import TEST_STATIC_DIR
from manage import app, initdb
# from pma_api.tasks import activate_dataset_request
from pma_api.manage.db_mgmt import restore_db_local, new_backup_path, \
    backup_local, restore_db_cloud, delete_s3_file, download_file_from_s3, \
    backup_db_cloud, backup_local_using_heroku_postgres, \
    restore_using_heroku_postgres
# write_data_file_to_db, \
# remove_stata_undefined_token_from_wb as \
# remove_stata_undefined_token_from_wb_imported


other_test_interference_tell = \
    'server closed the connection unexpectedly'
sleep_seconds = 10
max_attempts = 3


class PmaApiTest(unittest.TestCase):
    """Package super class"""

    @staticmethod
    def get_class_static_dir(_cls: str = '') -> str:
        """Get directory path for static files for calling class

        Args:
            _cls (str): Class name

        Returns:
            str: Designated static file dir for class
        """
        calling_class_name = _cls if _cls else \
            inspect.stack()[1][0].f_locals['self'].__class__.__name__
        dirname = TEST_STATIC_DIR + calling_class_name + '/'

        return dirname

    @classmethod
    def get_method_static_dir(cls, _cls: str = '', _mtd: str = '') -> str:
        """Get directory path for static files for calling method

        Args:
            _cls (str): Class name
            _mtd (str): Method name

        Returns:
            list: Designated static file dir for method
        """
        calling_method_name = _mtd if _mtd else inspect.stack()[1].function
        class_dir = cls.get_class_static_dir(_cls=_cls if _cls else '')
        dirname = class_dir + calling_method_name + '/'

        return dirname

    @classmethod
    def get_class_static_files(cls, _cls: str = '') -> List[str]:
        """Get paths to static files for calling class

        Args:
            _cls (str): Class name

        Returns:
            list: Designated static files for class
        """
        class_dir = cls.get_class_static_dir(_cls=_cls if _cls else '')
        files = glob(class_dir + '*')

        return files

    @classmethod
    def get_method_static_files(cls) -> List[str]:
        """Get paths to static files for calling method

        Returns:
            list: Designated static files for method
        """
        result = []

        prev_stack_vars = inspect.stack()[1][0].f_locals
        key = 'self' if 'self' in prev_stack_vars else 'cls'

        if isinstance(prev_stack_vars[key], type):
            calling_class_name = prev_stack_vars[key].__name__
        else:
            calling_class_name = prev_stack_vars[key].__class__.__name__

        calling_method_name = inspect.stack()[1].function

        method_dir_variations = (calling_method_name,
                                 calling_method_name.replace('test_', ''),
                                 'test_' + calling_method_name)

        for dirname in method_dir_variations:
            method_dir = cls.get_method_static_dir(_cls=calling_class_name,
                                                   _mtd=dirname)
            # I think Pycharm is wrong here. -jef
            # noinspection PyTypeChecker
            files = glob(method_dir + '*')
            result = files if files else result

        return result

    def setUp(self):
        """Set up: Put Flask app in test mode"""
        app.testing = True
        self.app = app.test_client()


class TestRoutes(PmaApiTest):
    """Test routes"""

    ignore_routes = ('/static/<path:filename>',
                     '/activate_dataset_request',  # POST
                     '/activate_dataset',  # POST
                     '/longtask',  # POST
                     '/data', '/datalab/data')  # TODO: temp, because slow
    ignore_end_patterns = ('>',)
    non_json_routes = ('/admin', '/docs')

    @staticmethod
    def valid_route(route):
        """Validate route.

        Args:
            route (str): Route url pattern.

        Returns:
            bool: True if valid, else False.
        """
        if route in TestRoutes.ignore_routes \
                or any(route.endswith(x) for x in TestRoutes.ignore_routes) \
                or route.endswith(TestRoutes.ignore_end_patterns):
            return False
        return True

    def _check_json_loads(self, routes: List[str], attempt: int = 1):
        """Check that routes all return a JSON response

        Args:
            routes (list): Routes to check
            attempt (int): Attempt iteration num. Exits if failures exceed max.
        """
        try:
            for route in routes:
                print('fetching: ' + route)
                r: Response = self.app.get(route)
                self.app.get(route)
                if route not in self.non_json_routes:
                    self.assertTrue(r.is_json)
        except OperationalError as err:  # Other tests may be interrupting this
            if other_test_interference_tell in str(err):
                time.sleep(sleep_seconds)
                if attempt >= max_attempts:
                    raise err
                self._check_json_loads(routes=routes, attempt=attempt + 1)

    def test_datalab_queries(self):
        """Test specific Datalab queries"""
        routes: List[str] = [  # Somewhat randomly selected
            # 3 rounds across 2 countries, line over time
            '/v1/datalab/combos?survey=PMA2014_BFR1,PMA2015_BFR2,PMA2014_ETR1&'
            'indicator=mcp_all&characteristicGroup=marital_status&',
            '/v1/datalab/data?survey=PMA2014_BFR1,PMA2015_BFR2,PMA2014_ETR1&in'
            'dicator=mcp_all&characteristicGroup=marital_status&overTime=true',
            # 1 country, 2 regions, bar
            '/v1/datalab/combos?survey=PMA2016_NER2&indicator=fees_12months_al'
            'l&characteristicGroup=region_NE',
            '/v1/datalab/data?survey=PMA2016_NER2&indicator=fees_12months_all&'
            'characteristicGroup=region_NE&',
            # another: 1 over time / 1 non
            '/v1/datalab/combos?survey=PMA2014_BFR1,PMA2015_BFR2,PMA2014_CDR2_'
            'Kinshasa,PMA2015_CDR3_Kinshasa,PMA2015_CDR4_Kinshasa,PMA2016_CDR5'
            '_Kinshasa,PMA2015_CDR4_KongoCentral,PMA2016_CDR5_KongoCentral&ind'
            'icator=visits_iud_new&characteristicGroup=beds&',
            '/v1/datalab/data?survey=PMA2014_BFR1,PMA2015_BFR2,PMA2014_CDR2_Ki'
            'nshasa,PMA2015_CDR3_Kinshasa,PMA2015_CDR4_Kinshasa,PMA2016_CDR5_K'
            'inshasa,PMA2015_CDR4_KongoCentral,PMA2016_CDR5_KongoCentral&indic'
            'ator=visits_iud_new&characteristicGroup=beds&',
            '/v1/datalab/data?survey=PMA2014_BFR1,PMA2015_BFR2,PMA2014_CDR2_Ki'
            'nshasa,PMA2015_CDR3_Kinshasa,PMA2015_CDR4_Kinshasa,PMA2016_CDR5_K'
            'inshasa,PMA2015_CDR4_KongoCentral,PMA2016_CDR5_KongoCentral&indic'
            'ator=visits_iud_new&characteristicGroup=beds&overTime=true&'
        ]
        self._check_json_loads(routes)

    def test_json_routes(self):
        """Smoke test routes: no runtime errors and return JSON"""
        routes: List[str] = [route.rule for route in app.url_map.iter_rules()
                             if self.valid_route(route.rule)]
        self._check_json_loads(routes)


# TODO
# class TestApplyDataOnlyDataset(PmaApiTest):
#     """Test that apply staging/production feature works"""
#
#     def setUp(self):
#         """Set up super and upload a test dataset"""
#         # Method1 - test client
#         #   Switch to this if want to use test client, but if so, using app
#         #   context will yield the following error:
#         #   AttributeError: 'FlaskClient' object has no attribute
#         'app_context'
#         # super().setUp()
#         # self.upload_test_dataset_to_self_db()
#
#         # Method 2 - real app client
#         self.app = app
#         with self.app.app_context():
#             self.upload_test_dataset_to_self_db()
#
#     def upload_test_dataset_to_self_db(self):
#         """Upload small test dataset to db running on same server as test"""
#         to_upload = self.get_method_static_files()
#         for file in to_upload:
#             write_data_file_to_db(filepath=file)
#         pass
#
#     def test_apply_dataset(self):
#         """Test"""
#         pass
#         activate_dataset_request(
#             dataset_name='',
#             destination_host_url=app.config.LOCAL_DEVELOPMENT_URL)


# TODO
# class TestFormatWorkbook(PmaApiTest):
#     """Tests for formatting operations on pre-loaded xlrd.book.Book objs"""
#
#     # Warning: If enabled, will erase DB.
#     db_overwrite_enabled = os.getenv('OVERWRITE_TEST_ENABLED', False)
#
#     # TODO: Appears to work; but don't know what I want the assert to be
#     @classmethod
#     def remove_stata_undefined_token_from_wb(cls):
#         """Decoupled method for easier debugging
#
#         Returns:
#             xlrd.book.Bookd: formatted workbook object
#         """
#         path = cls.get_method_static_files()[0]
#         with xlrd.open_workbook(path) as book:
#             formatted = remove_stata_undefined_token_from_wb_imported(book)
#
#         return formatted
#
#     # todo - finish
#     def test_remove_stata_undefined_token_from_wb(self):
#         """Test this particular function"""
#         # todo
#         # noinspection PyUnusedLocal
#         formatted = self.remove_stata_undefined_token_from_wb()
#
#         received = '?'
#         expected = '??'
#         self.assertEquals(received, expected)
#
#     # todo - finish
#     def test_upload_wb_with_stata_undefined_tokens(self):
#         """Test whether or not can be uploaded after formatting"""
#         # noinspection PyUnusedLocal
#         formatted = self.remove_stata_undefined_token_from_wb()
#
#         received = '?'
#         expected = '??'
#         self.assertEquals(received, expected)


# TODO - re-enable after staging deploy
# class TestDbFunctions(PmaApiTest):
#     """Test database functions"""
#
#     # Warning: If enabled, will erase DB.
#     db_overwrite_enabled = os.getenv('OVERWRITE_TEST_ENABLED', False)
#     backup_kb_threshold = 200
#     backup_msg = 'Backup file did not meet expected minimum threshold of {} ' \
#                  'kb.'.format(str(backup_kb_threshold))
#     live_test_app_name = 'pma-api-staging'
#
#     def setUp(self):
#         """Setup"""
#         self.backup: str = new_backup_path()
#         backup_local(path=self.backup)
#
#     def tearDown(self):
#         """Tear down"""
#         restore_db_local(path=self.backup)
#
#     @classmethod
#     def initdb_overwrite(cls, path: str = ''):
#         """Test"""
#         enabled = TestDbFunctions.db_overwrite_enabled
#         if enabled:
#             if path:
#                 initdb(overwrite=enabled, api_file_path=path)
#             else:
#                 initdb(overwrite=enabled)
#
#     @staticmethod
#     def backup_local_and_get_file_size(path: str = new_backup_path()):
#         """Backup db and return file size
#
#         Args:
#             path (str): Path to save backup file
#
#         Returns:
#             int: Size of backed up file in MB
#         """
#         backup_local(path=path)
#         size = os.path.getsize(path)
#         size_in_kb = size >> 10
#
#         return size_in_kb
#
#     @classmethod
#     def backup_restore_local_and_get_sizes(cls):
#         """Backup db, restore, backup again and return file sizes
#
#         Returns:
#             int, int: Relative, truncated file sizes, in mb
#         """
#         path_before = new_backup_path()
#         size_before = cls.backup_local_and_get_file_size(path_before)
#
#         restore_db_local(path=path_before)
#
#         path_after = new_backup_path()
#         size_after = cls.backup_local_and_get_file_size(path_after)
#
#         os.remove(path_before)
#         os.remove(path_after)
#
#         return size_before, size_after
#
#     @staticmethod
#     def backup_cloud_and_get_file_size(path: str = new_backup_path()):
#         """Backup db and return file size
#
#         Args:
#             path (str): Path to save backup file
#
#         Returns:
#             int: Size of backed up file in MB
#         """
#         from pma_api.config import BACKUPS_DIR
#
#         # with SuppressStdoutStderr():  # S3 has unfixed resource warnings
#         filename = backup_db_cloud(path)
#         dl_path = download_file_from_s3(filename=filename,
#                                         directory=BACKUPS_DIR)
#
#         size = os.path.getsize(path)
#         size_in_kb = size >> 10
#         os.remove(dl_path)
#
#         return size_in_kb
#
#     @classmethod
#     def backup_restore_cloud_and_get_sizes(cls):
#         """Backup db, restore, backup again and return file sizes
#
#         Returns:
#             int, int: Relative, truncated file sizes, in mb
#         """
#         import ntpath
#
#         path_before = new_backup_path()
#         filename_before = ntpath.basename(path_before)
#         size_before = cls.backup_cloud_and_get_file_size(path_before)
#
#         # with SuppressStdoutStderr():  # S3 has unfixed resource warnings
#         restore_db_cloud(filename=filename_before)
#
#         path_after = new_backup_path()
#         filename_after = ntpath.basename(path_after)
#         size_after = cls.backup_cloud_and_get_file_size(path_after)
#
#         for f in (path_before, path_after):
#             if os.path.exists(f):
#                 os.remove(f)
#         # with SuppressStdoutStderr():  # S3 has unfixed resource warnings
#         delete_s3_file(filename_before)
#         delete_s3_file(filename_after)
#
#         return size_before, size_after
#
#     @staticmethod
#     def backup_static_local(func, path: str = new_backup_path()) -> int:
#         """Static helper function for backup tests
#
#         Args:
#             func: Function to execute the actual backup
#             path (str): Path to save file
#
#         Returns:
#             int: Size in kb
#         """
#         size_in_kb = func(path)
#         if os.path.exists(path):
#             os.remove(path)
#
#         return size_in_kb
#
#     @classmethod
#     def backup_static_staging(cls, path: str = new_backup_path()) -> str:
#         """Backup staging database to local file system
#
#         Args:
#             path (str): Path to save file
#
#         Side effects:
#             - Saves file at path
#         """
#         path: str = backup_local_using_heroku_postgres(
#             path=path,
#             app_name=cls.live_test_app_name)
#
#         return path
#
#     @classmethod
#     def restore_static_staging(cls, path: str):
#         """Restore remote staging database from file
#
#         Args:
#             path (str): Path to locally saved file
#
#         Side effects:
#             - Restores remote database
#         """
#         # TODO: Color url - Yes, looks like it
#         # TODO: Signed backup?
#         # TODO: make same as in db_mgmt, or put inside restore func
#         filename: str = os.path.basename(path)
#         obj_key: str = S3_BACKUPS_DIR_PATH + filename
#         from_url_base = 'https://{bucket}.s3.amazonaws.com/{key}'
#         from_url: str = from_url_base.format(bucket=BUCKET, key=obj_key)
#
#         # TODO: rename from 'url' to 'name' and set all envs if needed
#         # to_url: str = os.getenv('STAGING_DB_URL')
#         to_url: str = os.getenv('STAGING_DB_NAME')
#
#         restore_using_heroku_postgres(
#             s3_signed_url=from_url,
#             db_url=to_url,
#             app_name=cls.live_test_app_name)
#
#     # def t1_backup_local(self):
#     #     """Test backup of db locally"""
#     #     if os.getenv('ENV_NAME') == 'development':
#     #         size: int = self.backup_static_local(
#     #             self.backup_local_and_get_file_size)
#     #         self.assertGreater(size, self.backup_kb_threshold,
#     #                            msg=self.backup_msg)
#     # #
#     # def t2_restore_local(self):
#     #     """Test restore of db from a local backup"""
#     #     hash_before, hash_after = self.backup_restore_local_and_get_sizes()
#     #
#     #     self.assertEqual(hash_before, hash_after)
#     #
#     # def t3_backup_cloud(self):
#     #     """Test backup of db to the cloud"""
#     #     size: int = self.backup_static_local(
#     #         self.backup_cloud_and_get_file_size)
#     #     self.assertGreater(size, self.backup_kb_threshold,
#     #                        msg=self.backup_msg)
#     #
#     # def t4_restore_cloud(self):
#     #     """Test restore of db from a cloud backup"""
#     #     hash_before, hash_after = self.backup_restore_cloud_and_get_sizes()
#     #
#     #     self.assertEqual(hash_before, hash_after)
#
#     def t5_backup_restore_on_staging(self):
#         """Restore database
#
#         Side effects:
#             - Reverts database to state of backup file
#         """
#         # TODO: Don't I need to upload to S3 after downloading?
#         path: str = self.backup_static_staging()
#         self.restore_static_staging(path)
#
#         self.assertTrue(True)  # no-op; If no errors until here, we're ok
#
#     # def t6_initdb_overwrite(self):
#     #     """Test initdb with full database overwrite without any exceptions"""
#     #     enabled = TestDbFunctions.db_overwrite_enabled
#     #     if enabled:
#     #         for file in self.get_method_static_files():
#     #             self.initdb_overwrite(path=file)
#     pass
#
#     def test_db_functions_sequentially(self):
#         """Test sequentially
#
#         Will find sequential tests by looking for any methods on test objects
#         that start with the pattern 't[0-9]_'.
#         """
#         from collections import OrderedDict
#
#         methods = {k: getattr(self, k) for k in dir(self)
#                    if callable(getattr(self, k))}
#         sequential_tests = OrderedDict({
#             k: v for k, v in methods.items()
#             if k[0] == 't' and
#             k[1] in [str(x) for x in range(10)] and
#             k[2] == '_'})
#         for name, func in sequential_tests.items():
#             print('Running sub-test: ' + name)
#             func()


class TestAsync(PmaApiTest):
    """Test async functions, e.g. task queue Celery and message broker"""

    def test_async(self):
        """Test async functions, e.g. task queue Celery and message broker"""
        pass


if __name__ == '__main__':
    pass
    from test import doctest_unittest_runner

    TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + '/'
    doctest_unittest_runner(test_dir=TEST_DIR, relative_path_to_root='../',
                            package_names=['pma_api', 'test'])

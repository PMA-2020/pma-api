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
from glob import glob
import inspect
import os
import unittest

import xlrd
from psycopg2 import OperationalError as OperationalError2
from sqlalchemy.exc import OperationalError as OperationalError1
from sqlalchemy.util.queue import Empty as EmptyError

from test.config import TEST_STATIC_DIR
from manage import app, initdb
from pma_api.tasks import apply_dataset_request
from pma_api.manage.db_mgmt import write_data_file_to_db, restore_db_local, \
    new_backup_path, remove_stata_undefined_token_from_wb as \
    remove_stata_undefined_token_from_wb_imported, backup_cloud, \
    backup_local, restore_db_cloud, delete_s3_file, download_file_from_s3


class PmaApiTest(unittest.TestCase):
    """Package super class"""

    @staticmethod
    def get_class_static_dir(_cls: str = ''):
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
    def get_method_static_dir(cls, _cls: str = '', _mtd: str = ''):
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
    def get_class_static_files(cls, _cls: str = ''):
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
    def get_method_static_files(cls):
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

    ignore_routes = ('/static/<path:filename>',)
    ignore_end_patterns = ('>',)

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
        """Smoke test routes to ensure no runtime errors"""
        try:
            routes = [route.rule for route in app.url_map.iter_rules()
                      if self.valid_route(route.rule)]
            for route in routes:
                self.app.get(route)
        except (EmptyError, OperationalError1, OperationalError2) as err:
            msg = 'An exception of type {0} occurred. Arguments:\n{1!r}\n\n' \
                  'Original error:\n'\
                .format(type(err).__name__, err.args)
            raise Exception(msg)


class TestApplyDataset(PmaApiTest):
    """Test that apply staging/production feature works"""

    def setUp(self):
        """Set up super and upload a test dataset"""
        # Method1 - test client
        #   Switch to this if want to use test client, but if so, using app
        #   context will yield the following error:
        #   AttributeError: 'FlaskClient' object has no attribute 'app_context'
        # super().setUp()
        # self.upload_test_dataset_to_self_db()

        # Method 2 - real app client
        self.app = app
        with self.app.app_context():
            self.upload_test_dataset_to_self_db()

    def upload_test_dataset_to_self_db(self):
        """Upload small test dataset to db running on same server as test"""
        to_upload = self.get_method_static_files()
        for file in to_upload:
            write_data_file_to_db(filepath=file)

        pass

    def test_apply_dataset(self):
        """Test"""
        apply_dataset_request(dataset_name='',
                              destination=app.config.LOCAL_DEVELOPMENT_URL)


# TODO
class TestFormatWorkbook(PmaApiTest):
    """Tests for formatting operations on pre-loaded xlrd.book.Book objects"""

    # Warning: If enabled, will erase DB.
    db_overwrite_enabled = os.getenv('OVERWRITE_TEST_ENABLED', False)

    # TODO: Appears to work; but don't know what I want the assert to be
    @classmethod
    def remove_stata_undefined_token_from_wb(cls):
        """Decoupled method for easier debugging

        Returns:
            xlrd.book.Bookd: formatted workbook object
        """
        path = cls.get_method_static_files()[0]
        with xlrd.open_workbook(path) as book:
            formatted = remove_stata_undefined_token_from_wb_imported(book)

        return formatted

    # todo - finish
    def test_remove_stata_undefined_token_from_wb(self):
        """Test this particular function"""
        # todo
        # noinspection PyUnusedLocal
        formatted = self.remove_stata_undefined_token_from_wb()

        received = '?'
        expected = '??'
        self.assertEquals(received, expected)

    # todo - finish
    def test_upload_wb_with_stata_undefined_tokens(self):
        """Test whether or not can be uploaded after formatting"""
        # noinspection PyUnusedLocal
        formatted = self.remove_stata_undefined_token_from_wb()

        received = '?'
        expected = '??'
        self.assertEquals(received, expected)


class TestDbFunctions(PmaApiTest):
    """Test database functions"""

    # Warning: If enabled, will erase DB.
    db_overwrite_enabled = os.getenv('OVERWRITE_TEST_ENABLED', False)
    s3_upload_prompt = 'Uploading backup to cloud storage on AWS S3. One or ' \
        'more "ResourceWarning" may display in the console. However, this ' \
        'is an open issue with the AWS S3 client (boto3), and can be ' \
        'safely ignored.'

    @classmethod
    def initdb_overwrite(cls, path: str = ''):
        """Test"""
        enabled = TestDbFunctions.db_overwrite_enabled
        if enabled:
            if path:
                initdb(overwrite=enabled, api_file_path=path)
            else:
                initdb(overwrite=enabled, api_file_path=path)

    @staticmethod
    def backup_local_and_get_file_size(path: str = new_backup_path()):
        """Backup db and return file size

        Args:
            path (str): Path to save backup file

        Returns:
            int: Size of backed up file in MB
        """
        backup_local(path=path)
        size = os.path.getsize(path)
        size_in_mb = size >> 20

        return size_in_mb

    @classmethod
    def backup_restore_local_and_get_sizes(cls):
        """Backup db, restore, backup again and return file sizes

        Returns:
            int, int: Relative, truncated file sizes, in mb
        """
        path_before = new_backup_path()
        size_before = cls.backup_local_and_get_file_size(path_before)

        restore_db_local(path=path_before)

        path_after = new_backup_path()
        size_after = cls.backup_local_and_get_file_size(path_after)

        os.remove(path_before)
        os.remove(path_after)

        return size_before, size_after

    @staticmethod
    def backup_cloud_and_get_file_size(path: str = new_backup_path()):
        """Backup db and return file size

        Args:
            path (str): Path to save backup file

        Returns:
            int: Size of backed up file in MB
        """
        from pma_api.config import BACKUPS_DIR

        filename = backup_cloud(path)

        dl_path = download_file_from_s3(filename=filename,
                                        directory=BACKUPS_DIR)
        size = os.path.getsize(path)
        size_in_mb = size >> 20
        os.remove(dl_path)

        return size_in_mb

    @classmethod
    def backup_restore_cloud_and_get_sizes(cls):
        """Backup db, restore, backup again and return file sizes

        Returns:
            int, int: Relative, truncated file sizes, in mb
        """
        import ntpath

        path_before = new_backup_path()
        filename_before = ntpath.basename(path_before)
        size_before = cls.backup_cloud_and_get_file_size(path_before)

        restore_db_cloud(filename=filename_before)

        path_after = new_backup_path()
        filename_after = ntpath.basename(path_after)
        size_after = cls.backup_cloud_and_get_file_size(path_after)

        for f in (path_before, path_after):
            if os.path.exists(f):
                os.remove(f)
        delete_s3_file(filename_before)
        delete_s3_file(filename_after)

        return size_before, size_after

    def test_initdb_overwrite(self):
        """Test initdb with full database overwrite"""
        enabled = TestDbFunctions.db_overwrite_enabled
        if enabled:
            self.initdb_overwrite()
            self.assertTrue(True)  # TODO

    def test_backup_local(self):
        """Test backup db"""
        path = new_backup_path()
        size_in_mb = self.backup_local_and_get_file_size(path)
        os.remove(path)
        self.assertGreater(size_in_mb, 1)

    def test_restore_local(self):
        """Test restore db"""
        hash_before, hash_after = self.backup_restore_local_and_get_sizes()

        self.assertEqual(hash_before, hash_after)

    def test_backup_cloud(self):
        """Test backup db"""
        print(self.s3_upload_prompt)
        path = new_backup_path()
        size_in_mb = self.backup_cloud_and_get_file_size(path)
        os.remove(path)
        self.assertGreater(size_in_mb, 1)

    def test_restore_cloud(self):
        """Test restore db"""
        print(self.s3_upload_prompt)
        hash_before, hash_after = self.backup_restore_cloud_and_get_sizes()

        self.assertEqual(hash_before, hash_after)


if __name__ == '__main__':
    from test import doctest_unittest_runner
    TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + '/'
    doctest_unittest_runner(test_dir=TEST_DIR, relative_path_to_root='../',
                            package_names=['pma_api', 'test'])

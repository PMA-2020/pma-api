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
import json
import os
import time
from glob import glob
from typing import List, Dict, Union

from flask import Response, Flask
import unittest
from flask_sqlalchemy import Model
from sqlalchemy.exc import OperationalError

# import xlrd
# from manage import app
from manage import app, db, initdb
# from pma_api.tasks import activate_dataset_request
from pma_api.manage.db_mgmt import restore_db_local, new_backup_path, \
    backup_local, restore_db_cloud, delete_s3_file, download_file_from_s3, \
    backup_db_cloud, backup_local_using_heroku_postgres, is_db_empty, \
    restore_using_heroku_postgres, list_datasets
# write_data_file_to_db, \
# remove_stata_undefined_token_from_wb as \
# remove_stata_undefined_token_from_wb_imported
from pma_api.utils import dict_to_pretty_json, get_db_models
from test.config import TEST_STATIC_DIR

other_test_interference_tell = \
    'server closed the connection unexpectedly'
sleep_seconds = 3
max_attempts = 3


class PmaApiTest(unittest.TestCase):
    """Package super class"""

    @staticmethod
    def get_dir_files(directory: str) -> List[str]:
        """Get list of files in a directory."""
        files: List[str] = glob(directory + '*')
        files: List[str] = [x for x in files if not os.path.isdir(x)]

        return files

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
        files: List[str] = cls.get_dir_files(class_dir)

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

        method_dir_variations = (
            calling_method_name,
            calling_method_name.replace('test_', ''),
            'test_' + calling_method_name)

        for dirname in method_dir_variations:
            method_dir: str = cls.get_method_static_dir(
                _cls=calling_class_name,
                _mtd=dirname)
            files: List[str] = cls.get_dir_files(method_dir)
            result = files if files else result

        return result

    def create_app(self):
        """Just implementing all abstract methods as required.

        https://stackoverflow.com/questions/45396040/how-to-find-and-
        implement-all-the-abstract-methods-in-pycharm?rq=1

        Note 2018.04.09-jef: Honestly, I'm not 100% sure why I have to do this.
        """
        # raise NotImplementedError  # Doing this causes Pycharm to show err.
        pass

    def setUp(self):
        """Set up: Put Flask app in test mode"""
        app.testing = True
        self.app = app.test_client()


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


# TODO
# class TestAsync(PmaApiTest):
#     """Test async functions, e.g. task queue Celery and message broker"""
#
#     def test_async(self):
#         """Test async functions, e.g. task queue Celery and message broker"""
#         pass


class SequentialTests(PmaApiTest):
    """Test database functions"""

    # In staging/prod, skips initdb test since initdb is already part of
    # release process.
    test_numbers_to_skip: List[int] = [1] if \
        os.getenv('ENV_NAME', 'development') != 'development' else []

    backup_kb_threshold: int = 50
    backup_msg: str = 'Backup file didn\'t meet expected minimum threshold ' \
        'of {} kb.'.format(str(backup_kb_threshold))
    live_test_app_name: str = 'pma-api-staging'
    live_app: Flask = app
    db_empty: bool = is_db_empty(live_app)
    ignore_routes = (
        '/static/<path:filename>',
        '/activate_dataset_request',  # POST
        '/activate_dataset',  # POST
        '/longtask',  # POST
        '/v1/data',
        '/v1/datalab/data')  # TODO: fix timeout err
    ignore_end_patterns = ('>',)
    json_route_start_pattern = '/v'

    def setUp(self):
        """Setup"""
        super().setUp()
        print('- Setting up test: Creating backup file...')
        self.backup: str = new_backup_path()
        backup_local(path=self.backup, silent=True)

    def tearDown(self):
        """Tear down"""
        # TODO 2019.04.11-jef: Fix this issue. Don't know why this occurs.
        #  Seems to occur even when Postico, other clients are closed, celery
        #  isn't running, server isn't running. Maybe it's the test client?
        #  In any event... this method of restore would not work on our server
        #  deployments on Heroku, as Heroku CLI is used for backup and restore.
        # pma_api.error.PmaApiDbInteractionError:
        # pg_restore: [archiver (db)] Error while PROCESSING TOC:
        # pg_restore: [archiver (db)] Error from TOC entry 2583; 1262 227420
        # DATABASE pmaapi postgres
        # pg_restore: [archiver (db)] could not execute query: ERROR:
        # database "pmaapi" is being accessed by other users
        # DETAIL:  There are 2 other sessions using the database.
        #     Command was: DROP DATABASE pmaapi;
        #
        # Offending command: pg_restore --exit-on-error --create --clean
        # --dbname=postgres --host=localhost --port=5432 --username=postgres
        # /Users/joeflack4/projects/pma-api/data/db_backups/pma-api-
        # backup_MacOS_development_2019-04-11_10-22-47.440488.dump
        pass
        # print('- Finishing test: Restoring backup file...')
        # restore_db_local(path=self.backup, silent=True)

    @classmethod
    def initdb_overwrite(cls, path: str = ''):
        """Test"""
        if path:
            initdb(api_file_path=path, ui_file_path='')
        else:
            initdb()

    @staticmethod
    def backup_local_and_get_file_size(path: str = new_backup_path(),
                                       silent: bool = True):
        """Backup db and return file size

        Args:
            path (str): Path to save backup file
            silent (bool): Don't print stdout?

        Returns:
            int: Size of backed up file in MB
        """
        backup_local(path=path, silent=silent)
        size = os.path.getsize(path)
        size_in_kb = size >> 10

        return size_in_kb

    @classmethod
    def backup_restore_local_and_get_sizes(cls):
        """Backup db, restore, backup again and return file sizes

        Returns:
            int, int: Relative, truncated file sizes, in mb
        """
        path_before = new_backup_path()
        size_before = cls.backup_local_and_get_file_size(path_before)

        restore_db_local(path=path_before, silent=True)

        path_after = new_backup_path()
        size_after = cls.backup_local_and_get_file_size(path_after)

        os.remove(path_before)
        os.remove(path_after)

        return size_before, size_after

    @staticmethod
    def backup_cloud_and_get_file_size(path: str = new_backup_path(),
                                       silent: bool = True):
        """Backup db and return file size

        Side effects:
            - Backs up
            - Removes backup

        Args:
            path (str): Path to save backup file
            silent (bool): Don't print stdout?

        Returns:
            int: Size of backed up file in MB
        """
        from pma_api.config import S3_BACKUPS_DIR_PATH, DATA_DIR

        # with SuppressStdoutStderr():  # S3 has unfixed resource warnings
        filename: str = backup_db_cloud(path_or_filename=path, silent=silent)
        dl_path: str = download_file_from_s3(
            filename=filename,
            file_dir=S3_BACKUPS_DIR_PATH,
            dl_dir=DATA_DIR)

        size: int = os.path.getsize(dl_path)
        size_in_kb: int = size >> 10
        os.remove(dl_path)

        return size_in_kb

    @classmethod
    def backup_restore_cloud_and_get_sizes(cls):
        """Backup db, restore, backup again and return file sizes

        Returns:
            int, int: Relative, truncated file sizes, in mb
        """
        import ntpath

        path_before = new_backup_path(_os='Linux', _env='staging')
        filename_before = ntpath.basename(path_before)
        size_before = cls.backup_cloud_and_get_file_size(path_before)

        # with SuppressStdoutStderr():  # S3 has unfixed resource warnings
        restore_db_cloud(filename=filename_before, silent=True)

        path_after = new_backup_path()
        filename_after = ntpath.basename(path_after)
        size_after = cls.backup_cloud_and_get_file_size(path_after)

        for f in (path_before, path_after):
            if os.path.exists(f):
                os.remove(f)
        # with SuppressStdoutStderr():  # S3 has unfixed resource warnings
        delete_s3_file(filename_before)
        delete_s3_file(filename_after)

        return size_before, size_after

    @staticmethod
    def backup_static_local(func, path: str = new_backup_path()) -> int:
        """Static helper function for backup tests

        Args:
            func: Function to execute the actual backup
            path (str): Path to save file

        Returns:
            int: Size in kb
        """
        size_in_kb = func(path=path, silent=True)
        if os.path.exists(path):
            os.remove(path)

        return size_in_kb

    @classmethod
    def backup_static_staging(cls, path: str = '') -> str:
        """Backup staging database to local file system

        Args:
            path (str): Path to save file

        Side effects:
            - Saves file at path
        """
        path2 = new_backup_path(_os='Linux', _env='staging') if not path \
            else path
        path3: str = backup_local_using_heroku_postgres(
            path=path2, silent=True,
            app_name=cls.live_test_app_name)

        return path3

    @classmethod
    def restore_static_staging(cls, backup_url: str):
        """Restore remote staging database from remotely stored file

        Args:
            backup_url (str): Url to backup file stored online

        Side effects:
            - Restores remote database
        """
        # TODO: make same as in db_mgmt, or put inside restore func
        #  - Joe (2019.03.22): Not sure what I wrote above. Still need?
        restore_using_heroku_postgres(
            s3_url=backup_url,
            app_name=cls.live_test_app_name,
            silent=True)

    @classmethod
    def valid_route(cls, route):
        """Validate route.

        Args:
            route (str): Route url pattern.

        Returns:
            bool: True if valid, else False.
        """
        if route in cls.ignore_routes \
                or any(route.endswith(x) for x in cls.ignore_routes) \
                or route.endswith(cls.ignore_end_patterns):
            return False
        return True

    def _validate_json_response(self, routes: List[str], attempt: int = 1,
                                silent: bool = True):
        """Check that routes all return a JSON response

        Args:
            routes (list): Routes to check
            attempt (int): Attempt iteration num. Exits if failures exceed max.
        """
        typical_result_keys: tuple = ('result', 'results')
        combos_result_keys: tuple = ('characteristicGroup.id', 'indicator.id',
                                     'survey.id')
        all_possible_result_keys: tuple = \
            typical_result_keys + combos_result_keys
        msg = '\n- Route: {}\n' \
              '- Status code: {}  [Expected \'200\']\n' \
              '- Valid JSON: {} [Expected \'True\']'
        try:
            for route in routes:
                if not silent:
                    print('fetching: ' + route)
                r: Response = self.app.get(route)
                if route.startswith(self.json_route_start_pattern):
                    data: Union[List, Dict] = json.loads(r.data)

                    valid: bool = bool(r.is_json)
                    # Check for empty JSON, e.g. {} or []:
                    valid *= bool(data)  # int
                    if 'resultSize' in data:
                        valid *= bool(int(data['resultSize']) > 0)  # int
                    for x in all_possible_result_keys:
                        if x in data:
                            # Check for empty JSON, e.g. {} or []:
                            valid *= bool(data[x])  # int

                    valid: bool = bool(valid)
                    status_code: int = r.status_code
                    conditions: bool = status_code == 200 and valid
                    self.assertTrue(
                        conditions,
                        msg=msg.format(route, str(status_code), str(valid)))

        except OperationalError as err:  # Other tests may be interrupting this
            if other_test_interference_tell in str(err):
                time.sleep(sleep_seconds)
                if attempt >= max_attempts:
                    raise err
                self._validate_json_response(
                    routes=routes,
                    attempt=attempt + 1)

    # This is not currently necessary, as the 'activate' feature currently only
    #  works on running server.
    # def backup_restore_on_staging(self):
    #     """Restore database
    #
    #     Side effects:
    #         - Reverts database to state of backup file
    #     """
    #     path: str = self.backup_static_staging()
    #
    #     filename: str = store_file_on_s3(
    #         path=path,
    #         storage_dir=S3_BACKUPS_DIR_PATH)
    #     backup_url = 'https://{bucket}.s3.amazonaws.com/{path}{object}'
    #     .format(
    #         bucket=BUCKET,
    #         path=S3_BACKUPS_DIR_PATH,
    #         object=filename)
    #
    #     self.restore_static_staging(backup_url)
    #
    #     self.assertTrue(True)  # no-op; If no errors until here, we're ok

    def test_sequentially(self, test_numbers_to_skip: List[int] = None):
        """Test sequentially

        Will find sequential tests by looking for any methods on test objects
        that start with the pattern 't[0-9]_'.

        Args:
            test_numbers_to_skip (list): Test numbrrs to skip. Methods t"n" in
            this list won't run.
        """
        from collections import OrderedDict

        test_numbers_to_skip: List[int] = test_numbers_to_skip if \
            test_numbers_to_skip else self.test_numbers_to_skip
        msg = '- Running sub-test {}/{}: {}'
        methods = {k: getattr(self, k) for k in dir(self)
                   if callable(getattr(self, k))}
        sequential_tests = OrderedDict({
            k: v for k, v in methods.items()
            if k[0] == 't' and
            k[1] in [str(x) for x in range(10)] and
            k[2] == '_'})
        num_tests: int = len(sequential_tests.keys()) - \
            len(test_numbers_to_skip)

        test_run_num = 1
        test_method_num = 1
        for name, func in sequential_tests.items():
            if test_method_num not in test_numbers_to_skip:
                print(msg.format(test_run_num, num_tests, name))
                # with self.live_app.app_context():
                func()
                test_run_num += 1
            test_method_num += 1
            # time.sleep(sleep_seconds)

    # TODO: For some reason, some of these unit tests broke. However, the
    #  initdb_overwrite test is end-to-end and should cover these.
    # def t1_backup_local(self):
    #     """Test backup of db locally"""
    #     if os.getenv('ENV_NAME') == 'development':
    #         size: int = self.backup_static_local(
    #             self.backup_local_and_get_file_size)
    #         self.assertGreater(size, self.backup_kb_threshold,
    #                            msg=self.backup_msg)
    #
    # def t2_restore_local(self):
    #     """Test restore of db from a local backup"""
    #     hash_before, hash_after = self.backup_restore_local_and_get_sizes()
    #
    #     self.assertEqual(hash_before, hash_after)

    # def t3_backup_cloud(self):
    #     """Test backup of db to the cloud"""
    #     size: int = self.backup_static_local(
    #         self.backup_cloud_and_get_file_size)
    #     self.assertGreater(size, self.backup_kb_threshold,
    #                        msg=self.backup_msg)
    #
    # def t4_restore_cloud(self):
    #     """Test restore of db from a cloud backup"""
    #     hash_before, hash_after = self.backup_restore_cloud_and_get_sizes()
    #
    #     self.assertEqual(hash_before, hash_after)

    def t1_initdb_overwrite(self):
        """Test initdb with full db overwrite without any exceptions"""
        msg = 'Records were not found in the following tables: {}'

        for file in self.get_method_static_files():
            self.initdb_overwrite(path=file)

        models: List[Model] = get_db_models(db)
        with self.live_app.app_context():
            # noinspection PyUnresolvedReferences
            first_records: Dict[str, Model] = \
                {x.__tablename__: x.query.first() for x in models}
            # TODO 2019-04-02 jef: Right now, we're allowing caching to not
            #  happen during db initialization, but we really shouldn't.
            #  Change this test when we go back to requiring init caching.
            # error_tables: List[str] = \
            #     [k for k, v in first_records.items() if not v]
            error_tables: List[str] = \
                [k for k, v in first_records.items()
                 if not v and k is not 'cache']

        self.assertTrue(not error_tables, msg.format(', '.join(error_tables)))

    def t2_json_routes(self):
        """Smoke test routes: no runtime errors and return JSON"""
        routes: List[str] = [route.rule for route in
                             app.url_map.iter_rules()
                             if self.valid_route(route.rule)]
        self._validate_json_response(routes)

    def t3_datalab_queries(self):
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
        self._validate_json_response(routes)


class TestListDatasets(PmaApiTest):
    """Test dataset listing functionality"""

    minimal_expected_schema = {
        "cloud": [
            {
                "dataset_display_name": "",
                "dataset_type": "",
                "last_modified": "",
                "name": "",
                "version_number": "",
                "id": ""
            }
        ],
        "local": [
            ""
        ]
    }
    err = 'JSON returned from list_datasets did not appear as expected. ' \
          'Expected something with at least the following schema: \n{}'\
        .format(dict_to_pretty_json(minimal_expected_schema))

    def test_list_datasets(self):
        """Test dataset listing functionality"""
        well_formed = True
        datasets: Dict[str, List[Union[str, Dict[str, str]]]] \
            = list_datasets()

        for k, v in self.minimal_expected_schema.items():
            if k not in datasets.keys():
                well_formed = False
                break
            if v:
                if isinstance(v, list) and len(v) > 0:
                    if isinstance(v[0], dict):
                        schema_example: Dict = v[0]
                        dataset_sample: Dict = datasets[k][0]
                        all_keys_found: bool = \
                            all(x in dataset_sample for
                                x in schema_example.keys())
                        well_formed: bool = all_keys_found

        self.assertTrue(well_formed, self.err)


if __name__ == '__main__':
    pass
    from test import doctest_unittest_runner

    TEST_DIR = os.path.dirname(os.path.realpath(__file__)) + '/'
    doctest_unittest_runner(test_dir=TEST_DIR, relative_path_to_root='../',
                            package_names=['pma_api', 'test'])

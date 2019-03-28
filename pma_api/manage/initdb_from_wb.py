"""Database management"""
import os
from collections import OrderedDict
from time import time
from typing import List, Dict, Union, Generator

import xlrd
from xlrd.book import Book
from flask import Flask, current_app
from sqlalchemy.exc import OperationalError


from pma_api.manage.multistep_task import MultistepTask
from pma_api.manage.db_mgmt import get_api_data, get_ui_data, \
    register_administrative_metadata, restore_db, backup_db, connection_error,\
    env_access_err_tell, env_access_err_msg, TRANSLATION_MODEL_MAP, \
    caching_error, drop_tables, METADATA_MODEL_MAP, ORDERED_MODEL_MAP, \
    get_datasheet_names, format_book, init_from_sheet, seed_users
from pma_api import db
from pma_api.error import PmaApiDbInteractionError
from pma_api.models import Cache, Characteristic, Data, Indicator, Survey


class InitDbFromWb(MultistepTask):
    """From a Workbook object, initialize database."""

    task_name = 'Initializing database from {}'
    restore_msg = 'An issue occurred. Restoring database to state it was in ' \
                  'prior to task initialization.'

    def __init__(
            self, _app: Flask = current_app,
            api_file_path: str = get_api_data(),
            ui_file_path: str = get_ui_data(),
            silent: bool = False,
            callback: Generator = None):
        """Task for creation of database

        Args:
            _app: Flask application for context
            silent: Don't print updates?
            api_file_path: path to "API data file" spec xls file
            ui_file_path: path to "UIdata file" spec xls file
            callback: Callback function for progress yields
        """
        self._app: Flask = _app
        self.api_file_path: str = api_file_path
        self.ui_file_path: str = ui_file_path
        self.backup_path: str = ''
        self.callback: Generator = callback
        self.warnings = {}
        self.final_status = {
            'success': False,
            'seconds_elapsed': 0,
            'warnings': self.warnings,
        }
        super().__init__(
            silent=silent, callback=callback, subtasks=self.create_subtasks(),
            name=self.task_name.format(os.path.basename(api_file_path)))

    def create_subtasks(self) -> Dict[str, Dict[str, Union[str, int]]]:
        """Get a list of collection of subtask dict objects

        Concerns:
            What if order created for each metadata / data table is different
            here than what happens at runtime? Perhaps that's possible?

        Returns:
            dict: Collection of subtask objects
        """
        sub_tasks_static: Dict[str, Dict[str, Union[str, int]]] = {
            'backup1': {
                'prints': 'Backing up database',
                'pct_starts_at': 0,  # 0-9
                'func': self._backup1
            },
            'reset_db': {
                'prints': 'Resetting db for fresh install',
                'pct_starts_at': 10,  # 10-14
                'func': self._reset_db
            },
            # Metadata: 15-29
            'translations1': {
                'prints': 'Updating translations',
                'pct_starts_at': 30,  # 31-34
                'func': None
            },
            # Data: 35-89
            'translations2': {
                'prints': 'Updating translations',
                'pct_starts_at': 90,  # 90-91
                'func': None
            },
            'create_cache': {
                'prints': 'Caching',
                'pct_starts_at': 92,  # 92-94
                'func': self._create_cache
            },
            'backup2': {
                'prints': 'Backing up and finishing',
                'pct_starts_at': 95,  # 95-99
                'func': self._backup2
            }
        }

        # TODO: Build up and add funcs. Will require a change as well in run()
        # Metadata: 15-29
        metadata_list: List[Dict[str, Dict[str, Union[str, int]]]] = [
            {
                'upload_metadata_{}'.format(x[1].__tablename__): {
                    'prints': 'Uploading metadata - {}'.format(
                        x[1].__tablename__),
                    'pct_starts_at': int,
                    'func': None
                }
            } for x in METADATA_MODEL_MAP
        ]
        metadata_dict: Dict[str, Dict[str, Union[str, int]]] = \
            self._calc_subtask_grp_pcts(
            subtask_grp_list=metadata_list, start=15, stop=29)

        # Data: 35-89
        data_list: List[Dict[str, Dict[str, Union[str, int]]]] = [
            {
                'upload_data_{}'.format(x): {
                    'prints': 'Uploading data - {}'.format(x),
                    'pct_starts_at': int,
                    'func': None
                }
            } for x in get_datasheet_names(self.api_file_path)
        ]
        data_dict: Dict[str, Dict[str, Union[str, int]]] = \
            self._calc_subtask_grp_pcts(
            subtask_grp_list=data_list, start=35, stop=89)

        sub_tasks_unsorted: Dict[str, Dict[str, Union[str, int]]] = {
            **sub_tasks_static,
            **metadata_dict,
            **data_dict}

        # Pycharm thinks it will get a List[str], but is wrong.
        # noinspection PyTypeChecker
        sub_tasks_tuples: List[tuple] = sorted(
            sub_tasks_unsorted.items(),
            key=lambda x: x[1]['pct_starts_at'])
        sub_tasks: Dict[str, Dict[str, Union[str, int]]] = \
            OrderedDict(sub_tasks_tuples)

        return sub_tasks

    def init_from_workbook(self, wb_path: str, queue: tuple):
        """Init from workbook.

        Side effects:
            - Calls functions that write to DB

        Args:
            wb_path (str): path to workbook file
            queue (tuple): Order in which to load db_models.
        """
        metadata_queue: tuple = tuple(x for x in queue if x[0] != 'data')

        with xlrd.open_workbook(wb_path) as book:
            formatted: xlrd.book.Book = format_book(book)
            self.init_structural_metadata(wb=formatted, queue=metadata_queue)
            self.init_data(book)
            register_administrative_metadata(wb_path)

    def init_structural_metadata(self, wb: Book, queue: tuple):
        """Init structural metadata

        Side effects:
            - Writes to DB

        Args:
            wb (xlrd.book.Book): Dataset workbook object
            queue (tuple): Order in which to load db models
        """
        for sheetname, model in queue:
            # to-do 2019-04-02 jef: This probably needs a refactor; translation
            # should have its own function
            if sheetname == 'translation':
                current_pct: float = self.completion_ratio
                translations1_pct = float(
                    self.subtasks['translations1']['pct_starts_at'] / 100)
                subtask_name: str = 'translations' + \
                    ('1' if current_pct <= translations1_pct else '2')
                self.begin(subtask_name)
            else:
                self.begin('upload_metadata_{}'.format(model.__tablename__))

            ws: xlrd.sheet.Sheet = wb.sheet_by_name(sheetname)
            init_from_sheet(ws=ws, model=model)
        db.session.commit()

    def init_data(self, wb: xlrd.Book):
        """Put all the data from the workbook into the database.

        Args:
            wb (xlrd.Book): A spreadsheet
        """
        survey = {x.code: x.id for x in Survey.query.all()}
        indicator = {x.code: x.id for x in Indicator.query.all()}
        characteristic = {x.code: x.id for x in Characteristic.query.all()}
        data_sheets: List[xlrd.sheet] = \
            [x for x in wb.sheets() if x.name.startswith('data')]

        for ws in data_sheets:
            self.begin('upload_data_{}'.format(ws.name))
            init_from_sheet(ws=ws, model=Data, survey=survey,
                            indicator=indicator, characteristic=characteristic)

    def _backup1(self):
        """Back up before doing initialization"""
        try:
            self.backup_path: str = backup_db()
        except Exception as err:
            self.warnings['backup_1'] = str(err)

    def _reset_db(self):
        """Reset database

        Side effects:
            - Drops all data and schema
            - Creates new schema
            - Seeds initial, default users
        """
        drop_tables()
        self._create_schema()
        seed_users()

    @staticmethod
    def _create_schema():
        """Create DB schema"""
        db.create_all()

    def _create_cache(self):
        """Cache specific routes"""
        try:
            Cache.cache_datalab_init(self._app)
        except RuntimeError as err:
            self.warnings['caching'] = caching_error.format(err)

    def _backup2(self):
        """Back up resulting database"""
        try:
            self.backup_path: str = backup_db()
        except Exception as err:
            self.warnings['backup_2'] = str(err)

    def _execute_subtasks(self):
        """Execute database initialization.

        Side effects:
            - Creates database schema (tables, etc)
            - Seeds values into database
            - Backs up database: at the beginning and end of task execution

        # TODO 2019-04-02 jef
           1: Where to initialize translation1 and translation2 subtasks?
           2: Split up translations into their own functions
           3: For some reason, Geogrpahy label_id arent being populated
        """
        # TODO: 1. Refactor each subtask into a subtask obj
        #  replace dict w/ that
        # TODO: 2. Make sure translations are being made.they appear as subtask
        #  but dont appear here
        # TODO: 3. refactor so that each workbook init is a subtask. then,
        #  we can iterate through the subtasks ordered dict

        self.begin('backup1')
        self.begin('reset_db')

        # Seed database
        self.init_from_workbook(
            # wb_path=self.api_file_path, queue=METADATA_MODEL_MAP)
            wb_path=self.api_file_path, queue=ORDERED_MODEL_MAP)
        self.init_from_workbook(
            wb_path=self.ui_file_path, queue=TRANSLATION_MODEL_MAP)

        self.begin('create_cache')
        self.begin('backup2')

    def run(self) -> Dict:
        """Create a fresh database instance.

        Runs task execution, handles errors, and reports result.

        Returns:
            dict: Final results
        """
        start_time = time()
        self.begin()

        with self._app.app_context():
            try:
                self._execute_subtasks()
            except (OperationalError, AttributeError) as err:
                db.session.rollback()
                restore_db(self.backup_path)
                print(self.restore_msg)

                msg: str = str(err)
                if isinstance(err, OperationalError):
                    msg: str = connection_error.format(str(err))
                elif isinstance(err, AttributeError):
                    if env_access_err_tell in str(err):
                        msg: str = env_access_err_msg\
                            .format(type(err).__name__ + ': ' + str(err))
                raise PmaApiDbInteractionError(msg)

        seconds_elapsed = int(time() - start_time)
        self.final_status['seconds_elapsed'] = seconds_elapsed
        self.final_status['success'] = True
        self.complete(seconds_elapsed=seconds_elapsed)

        return self.final_status

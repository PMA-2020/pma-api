"""Database management"""
import os
from collections import OrderedDict
from time import time
from typing import List, Dict, Union, Generator

import xlrd
from flask import Flask, current_app
from sqlalchemy.exc import OperationalError, DatabaseError

from pma_api.manage.functional_subtask import FunctionalSubtask
from pma_api.manage.multistep_task import MultistepTask
from pma_api.manage.db_mgmt import get_api_data, get_ui_data, \
    register_administrative_metadata, restore_db, backup_db, connection_error,\
    env_access_err_tell, env_access_err_msg, caching_error, drop_tables, \
    ORDERED_METADATA_SHEET_MODEL_MAP, DATASET_WB_SHEET_MODEL_MAP, \
    get_datasheet_names, commit_from_sheet, seed_users
from pma_api import db
from pma_api.error import PmaApiDbInteractionError
from pma_api.models import Cache, Characteristic, Indicator, Survey


class InitDbFromWb(MultistepTask):
    """From a Workbook object, initialize database.

    # TODO 2019-04-02 jef
       - For some reason, geography label_id arent being populated
    """

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
        self.indicator_code_ids: Dict[str, int] = {}
        self.characteristic_code_ids: Dict[str, int] = {}
        self.survey_code_ids: Dict[str, int] = {}
        self.final_status = {
            'success': False,
            'seconds_elapsed': 0,
            'warnings': self.warnings,
        }
        # /Users/joeflack4/projects/pma-api/api_data-2019.01.22-v36-jef.xlsx
        with xlrd.open_workbook(api_file_path) as book:
            self.api_wb: xlrd.book.Book = book
        self.ui_wb = None
        if ui_file_path:
            with xlrd.open_workbook(ui_file_path) as book:
                self.ui_wb: xlrd.book.Book = book
        with _app.app_context():
            subtasks: Dict[str, Dict[str, Union[str, int]]] = \
                self.create_subtasks()
        self.subtask_queue: List[str] = [x for x in subtasks.keys()]

        super().__init__(
            silent=silent, callback=callback, subtasks=subtasks,
            name=self.task_name.format(os.path.basename(api_file_path)))

    def create_subtasks(self) -> Dict[str, Dict[str, Union[str, int]]]:
        """Get a list of collection of subtask dict objects

        Concerns:
            What if order created for each metadata / data table is different
            here than what happens at runtime? Perhaps that's possible?

        Returns:
            dict: Collection of subtask objects
        """
        # TODO 2019.04.04-jef: 1. Refactor subtask dicts to subtask class objs
        #  ...afterwards, edits can be made to MultistepTask class to remove
        #  the ugly 'if dict, do this, else...' conditionals.
        sub_tasks_static: Dict[str, Dict[str, Union[str, int]]] = {
            'backup1': {
                'prints': 'Backing up database',
                'pct_starts_at': 0,  # 0-9
                'func': lambda x=1: self._backup(num=x)
            },
            'reset_db': {
                'prints': 'Resetting db for fresh install',
                'pct_starts_at': 10,  # 10-14
                'func': self._reset_db
            },
            # Metadata: 15-29
            'translations_api': {
                'prints': 'Uploading metadata language translations',
                'pct_starts_at': 30,  # 31-34
                'func': lambda: self.init_api_worksheet('translation')
            },
            # Data: 35-89
            'translations_ui': {
                'prints': 'Uploading UI language translations',
                'pct_starts_at': 90,  # 90-91
                'func': self.init_client_ui_data
            },
            'create_cache': {
                'prints': 'Caching',
                'pct_starts_at': 92,  # 92-94
                'func': self._create_cache
            },
            'backup2': {
                'prints': 'Backing up and finishing',
                'pct_starts_at': 95,  # 95-99
                'func': lambda x=2: self._backup(num=x)
            }
        }

        metadata_list: List[Dict[str, FunctionalSubtask]] = [
            {
                'upload_metadata_{}'.format(v.__tablename__):
                    FunctionalSubtask(
                        name='upload_metadata_{}'.format(v.__tablename__),
                        prints='Uploading metadata - {}'
                        .format(v.__tablename__),
                        pct_starts_at=float(0),  # Temp until pct calculated
                        func=self.init_api_worksheet,
                        sheetname=k)
            } for k, v in ORDERED_METADATA_SHEET_MODEL_MAP.items()  # str,Model
        ]
        metadata_dict: Dict[str, Dict[str, Union[str, float]]] = \
            self._calc_subtask_grp_pcts(
            subtask_grp_list=metadata_list, start=15, stop=29)

        # Data: 35-89
        data_list: List[Dict[str, FunctionalSubtask]] = [
            {
                'upload_data_{}'.format(x):
                    FunctionalSubtask(
                        name='upload_data_{}'.format(x),
                        prints='Uploading data - {}'.format(x),
                        pct_starts_at=float(0),  # Temp until pct calculated
                        func=self.init_api_worksheet,
                        sheetname=x)
            } for x in get_datasheet_names(self.api_file_path)  # List[str]
        ]

        data_dict: Dict[str, Dict[str, Union[str, int]]] = \
            self._calc_subtask_grp_pcts(
            subtask_grp_list=data_list, start=float(35), stop=float(89))

        sub_tasks_unsorted: Dict[str, Dict[str, Union[str, float]]] = {
            **sub_tasks_static,
            **metadata_dict,
            **data_dict}

        # Pycharm thinks it will get a List[str], but is wrong.
        # noinspection PyTypeChecker
        sub_tasks_tuples: List[tuple] = sorted(
            sub_tasks_unsorted.items(),
            key=lambda x: x[1]['pct_starts_at']
            if isinstance(x[1], dict)  #
            else x[1].pct_starts_at)
        sub_tasks: Dict[str, Dict[str, Union[str, float]]] = \
            OrderedDict(sub_tasks_tuples)

        return sub_tasks

    def init_client_ui_data(self):
        """Load client UI language data into DB

        Side effects:
            - xlrd.open_workbook
            - commit_from_sheet
        """
        sheetname: str = 'translation'
        if self.ui_wb:
            commit_from_sheet(
                ws=self.ui_wb.sheet_by_name(sheetname),  # Sheet
                model=DATASET_WB_SHEET_MODEL_MAP[sheetname]),  # db.Model

    def set_relational_metadata(self):
        """Set instance attrs for required relational keys for 'Data' upload

        Side effects:
            - setattr
        """
        # to-do 2019-04-04-jef: Not sure how to implement this dynamic code
        model_attrs: Dict = {  # Dict[str,db.Model]
            'survey_code_ids': Survey,
            'indicator_code_ids': Indicator,
            'characteristic_code_ids': Characteristic
        }
        with self._app.app_context():
            for attr_name, model in model_attrs.items():
                val: Dict[str, int] = {x.code: x.id for x in model.query.all()}
                setattr(self, attr_name, val)

    def init_api_worksheet(self, sheetname: str, **kwargs):
        """Init metadata worksheet

        Side effects:
            - commit_from_sheet

        Args:
            sheetname (str): Name of worksheet for a model
            **kwargs: Additional keyword arguments to unpack and repack
            into init_from_worksheet.
        """
        if sheetname.startswith('data'):
            self.init_api_data_worksheet(sheetname)
        else:
            commit_from_sheet(
                ws=self.api_wb.sheet_by_name(sheetname),  # Sheet
                model=DATASET_WB_SHEET_MODEL_MAP[sheetname],  # db.Model
                **kwargs)

    def init_api_data_worksheet(self, sheetname: str):
        """Init data worksheet

        Side effects:
            - Creates records in db
            - Creates instance attributes if not already exist

        Args:
            sheetname (str): Name of worksheet containing data
        """
        # Init required instance variables if not already done
        required_relational_id_models: tuple = \
            ('survey', 'indicator', 'characteristic')
        attr_names: List[str] = \
            [x + '_code_ids' for x in required_relational_id_models]
        if any(not getattr(self, x) for x in attr_names):
            self.set_relational_metadata()

        commit_from_sheet(
            ws=self.api_wb.sheet_by_name(sheetname),
            model=DATASET_WB_SHEET_MODEL_MAP['data'],
            survey=self.survey_code_ids,
            indicator=self.indicator_code_ids,
            characteristic=self.characteristic_code_ids)

    def _backup(self, num: int = None):
        """Backup state of database

        Side Effects:
            - Backs up database
            - Mutates instance attributes

        Args:
            num (int): Represents the "n'th" backup being performed during
            execution of task. Backups can happen more than once per task,
            but only the latest successful backup is stored.
        """
        nth_backup_key: str = 'backup' if not num else 'backup_{}'.format(num)
        try:
            self.backup_path: str = backup_db()
        except Exception as err:
            self.warnings[nth_backup_key] = str(err)

    def _reset_db(self):
        """Reset database

        Side effects:
            - Drops all data and schema
            - Creates new schema
            - Seeds initial, default users
            - Registers administrative metadata
        """
        drop_tables()
        self._create_schema()
        seed_users()
        register_administrative_metadata(self.api_file_path)
        register_administrative_metadata(self.ui_file_path)

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
                for subtask_name in self.subtask_queue:
                    self.begin(subtask_name)
            except (DatabaseError, AttributeError) as err:
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

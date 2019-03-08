"""Database management"""
import csv
import glob
import logging
import ntpath
import os
import subprocess
from copy import copy
from datetime import datetime
from time import time
from typing import List, Tuple, Dict

import xlrd
import sqlalchemy
from flask import Flask, current_app
# noinspection PyProtectedMember
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DatabaseError, OperationalError, IntegrityError

from pma_api import create_app, db
from pma_api.config import DATA_DIR, BACKUPS_DIR, Config, \
    IGNORE_SHEET_PREFIX, DATA_SHEET_PREFIX, AWS_S3_STORAGE_BUCKETNAME as \
    BUCKET, S3_BACKUPS_DIR_PATH, S3_DATASETS_DIR_PATH, S3_UI_DATA_DIR_PATH, \
    UI_DATA_DIR, DATASETS_DIR, API_DATASET_FILE_PREFIX as API_PREFIX, \
    UI_DATASET_FILE_PREFIX as UI_PREFIX, HEROKU_INSTANCE_APP_NAME as APP_NAME,\
    FILE_LIST_IGNORES
from pma_api.error import InvalidDataFileError, PmaApiDbInteractionError, \
    PmaApiException
from pma_api.models import (Cache, Characteristic, CharacteristicGroup,
                            Country, Data, EnglishString, Geography, Indicator,
                            ApiMetadata, Survey, Translation, Dataset)
from pma_api.utils import most_common
from pma_api.manage.utils import log_process_stderr, run_proc


METADATA_MODEL_MAP = (
    ('geography', Geography),
    ('country', Country),
    ('survey', Survey),
    ('char_grp', CharacteristicGroup),
    ('char', Characteristic),
    ('indicator', Indicator),
)
DATA_MODEL_MAP = (
    ('data', Data),
)
TRANSLATION_MODEL_MAP = (
    ('translation', Translation),
)
ORDERED_MODEL_MAP = TRANSLATION_MODEL_MAP + METADATA_MODEL_MAP + DATA_MODEL_MAP
OVERWRITE_DROP_TABLES: Tuple[db.Model] = (
        x.__table__ for x in [
            EnglishString,
            Data,
            Translation,
            Indicator,
            Characteristic,
            CharacteristicGroup,
            Survey,
            Country,
            Geography,
            Cache,
            ApiMetadata])
root_connection_info = {
    'hostname': Config.DB_ROOT_HOST,
    'port': Config.DB_ROOT_PORT,
    'database': Config.DB_ROOT_NAME,
    'username': Config.DB_ROOT_USER,
    'password': Config.DB_ROOT_PASS}
db_connection_info = {
    'hostname': Config.DB_HOST,
    'port': Config.DB_PORT,
    'database': Config.DB_NAME,
    'username': Config.DB_USER,
    'password': Config.DB_PASS}
connection_error = 'Was not able to connect to the database. Please '\
    'check that it is running, and your database URL / credentials are ' \
    'correct.\n\n' \
    'Original error:\n' \
    '{}'
caching_error = 'Warning: Error occurred while trying to cache data after ' \
    'import. Is the server running?\n' \
    '- Side effects: The first time any cache-relevant routes ' \
    '(e.g. datalab/init) are loaded, they will load slower. ' \
    'However, at that time, an attempt will be made to cache ' \
    'again.\n' \
    '- Original error:\n' \
    '{}'
db_mgmt_err = 'An error occurred during db management procedure. This is ' \
    'probably due to the database being currently accessed.  The connection ' \
    'could be, for example, be a db browsing client such as psql, pgadmin, ' \
    'etc. These or any other active connections must closed before proceeding'\
    '. If closing such clients still does not solve the issue, try shutting ' \
    'down the server as well.'
db_not_exist_tell = 'database "{}" does not exist'\
    .format(os.getenv('DB_NAME', 'pmaapi'))
env_access_err_tell = "'NoneType' object has no attribute 'drivername'"
env_access_err_msg = \
    'An error occurred while interacting with the database. This can often ' \
    'happen when db related environmental variables (e.g. DATABASE_URL) are ' \
    'not set or cannot be accessed. Please check that they are set and ' \
    'being loaded correctly.\n\n' \
    '- Original error:\n{}'


class TaskTracker:
    """Tracks progress of task queue"""

    def __init__(self, queue: List[str] = [], silent: bool = False,
                 name: str = '', callback=None):
        """Tracks progress of task queue

        If queue is empty, calls to TaskTracker methods will do nothing.

        Args:
            queue (list): List of progress statements to display for each
            iteration of the queue.
            silent (bool): Print progress statements?
            callback: Callback function to use for every iteration
            of the queue. This callback must take a single dictionary as its
            parameter, with the following schema...
                {'status': str, 'current': float}
            ...where the value of 'current' is a float with value between 0
            and 1.
        """
        self.queue: List[str] = queue
        self.silent: bool = silent
        self.name = name
        self.callback = callback
        self.tot_sub_tasks: int = len(queue)
        self.status: str = 'PENDING'
        self.completion_ratio: float = float(0)

    def _report(self, silence_status: bool = False,
                silence_percent: bool = False):
        """Report progress

        Args:
            silence_status (bool): Silence status?
            silence_percent (bool): Silence percent?
        """
        if not self.queue:
            return
        if not self.silent:
            pct: str = str(int(self.completion_ratio * 100)) + '%'
            msg = ' '.join([
                self.status if not silence_status else '',
                '({})'.format(pct) if not silence_percent else ''
            ])
            print(msg)
        if self.callback:
            self.callback.send({'status': self.status,
                                'current': self.completion_ratio})

    def begin(self):
        """Register and report task begin

        Usage optional
        """
        if not self.queue:
            return
        self.completion_ratio: float = float(0)
        self.status: str = 'Task start: ' + \
                           ' {}'.format(self.name) if self.name else ''
        self._report(silence_percent=True)

    def next(self):
        """Register and report next sub-task begin"""
        if not self.queue:
            return
        self.completion_ratio: float = \
            1 - (len(self.queue) / self.tot_sub_tasks)
        first_task: bool = self.completion_ratio == 0
        if first_task:
            self.begin()
        self.status: str = self.queue.pop(0)
        self._report()

    def complete(self):
        """Register and report all sub-tasks and task itself complete

        Usage optional
        """
        if not self.queue:
            return
        self.completion_ratio: float = float(1)
        self.status: str = 'Task complete: ' + \
                           ' {}'.format(self.name) if self.name else ''
        self._report()


def aws_s3(func):
    """AWS S3 Wrapper

    This wrapper is not to be called directly, but should be used in the
    following way:

      @aws_s3
      def my_function_that_uses_s3(...):
        ...

    This wrapper provides the following functions:
        - Offers guidance in the event of connection issues
        - Prints out status update before calling function
        - Suppresses buggy, unfixed resource warnings from boto3 S3 client

    Args:
        func (function): This will be the function wrapped, e.g.
        'my_function_that_uses_s3' in the above example.

    Returns:
         function: The wrapped function
    """

    msg = '\nAccess was denied when attempting to interact with AWS S3. ' \
        'Please check the following: ' \
        '\n1. That you have set the following environment variables: ' \
        'AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY' \
        '\n2. The credentials specified in the environment variables are ' \
        'correct' \
        '\n3. The variables are able to be accessed. If, for example, ' \
        'you are using an IDE or tester, make sure that it has access to' \
        'the afforementioned environmental variables.'
    from botocore.exceptions import ClientError

    def wrap(*args, **kwargs):
        """Wrapped function"""
        verbose = kwargs and 'verbose' in kwargs and kwargs['verbose']
        if verbose:
            print('Executing: ' + func.__name__)
        wrapper_kwargs_removed = \
            {k: v for k, v in kwargs.items() if k != 'silent'}
        try:
            from test import SuppressStdoutStderr

            if verbose:
                return func(*args, **wrapper_kwargs_removed)
            with SuppressStdoutStderr():  # S3 has unfixed resource warnings
                return func(*args, **wrapper_kwargs_removed)
        except ClientError as err:
            if 'Access Denied' in str(err) or 'AccessDenied' in str(err):
                raise PmaApiDbInteractionError(msg)
            else:
                raise err

    return wrap


def get_data_file_by_glob(pattern):
    """Get file by glob.

    Args:
        pattern (str): A glob pattern.

    Returns:
        str: Path/to/first_file_found

    Raises:
        PmaApiException: If more was found than expected
    """
    found: List = glob.glob(pattern)
    if len(found) > 1:
        raise PmaApiException('Expected only 1 file to be found, but '
                              'discovered the following: \n' + str(found))
    return found[0] if found else ''


def get_api_data():
    """Get API data."""
    pattern: str = API_PREFIX + '*.xlsx'
    return get_data_file_by_glob(os.path.join(DATA_DIR, pattern))


def get_ui_data():
    """Get API data."""
    pattern: str = UI_PREFIX + '*.xlsx'
    return get_data_file_by_glob(os.path.join(DATA_DIR, pattern))


def make_shell_context():
    """Make shell context, for the ability to manipulate these db_models/tables
    from the command line shell.

    Returns:
        dict: Context for application manager shell.
    """
    return dict(app=create_app(os.getenv('ENV_NAME', 'default')), db=db,
                Country=Country, EnglishString=EnglishString,
                Translation=Translation, Survey=Survey, Indicator=Indicator,
                Data=Data, Characteristic=Characteristic, Cache=Cache,
                CharacteristicGroup=CharacteristicGroup,
                ApiMetadata=ApiMetadata, Dataset=Dataset)


def init_from_source(path, model):
    """Initialize DB table data from csv file.

    Initialize table data from csv source data files associated with the
    corresponding data model.

    Args:
        path (str): Path to csv data file.
        model (class): SqlAlchemy model class.
    """
    with open(path, newline='', encoding='utf-8') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            record = model(**row)
            db.session.add(record)
        db.session.commit()


def init_data(wb: xlrd.Book, progress_updater: TaskTracker = TaskTracker()):
    """Put all the data from the workbook into the database.

    Args:
        wb (xlrd.Book): A spreadsheet
        progress_updater (TaskTracker): Tracks progress of task queue
    """
    survey = {x.code: x.id for x in Survey.query.all()}
    indicator = {x.code: x.id for x in Indicator.query.all()}
    characteristic = {x.code: x.id for x in Characteristic.query.all()}
    data_sheets: List[xlrd.sheet] = \
        [x for x in wb.sheets() if x.name.startswith('data')]

    for ws in data_sheets:
        progress_updater.next()
        init_from_sheet(ws, Data, survey=survey, indicator=indicator,
                        characteristic=characteristic)


def init_from_sheet(ws, model, **kwargs):
    """Initialize DB table data from XLRD Worksheet.

    Initialize table data from source data associated with the corresponding
    data model.

    Args:
        ws (xlrd.sheet.Sheet): XLRD worksheet object.
        model (class): SqlAlchemy model class.
    """
    survey, indicator, characteristic = '', '', ''
    if model == Data:
        survey = kwargs['survey']
        indicator = kwargs['indicator']
        characteristic = kwargs['characteristic']
    header = None

    for i, row in enumerate(ws.get_rows()):
        row = [r.value for r in row]
        if i == 0:
            header = row
        else:
            row_dict = {k: v for k, v in zip(header, row)}
            if model == Data:
                survey_code = row_dict.get('survey_code')
                survey_id = survey.get(survey_code)
                row_dict['survey_id'] = survey_id
                indicator_code = row_dict.get('indicator_code')
                indicator_id = indicator.get(indicator_code)
                row_dict['indicator_id'] = indicator_id
                char1_code = row_dict.get('char1_code')
                char1_id = characteristic.get(char1_code)
                row_dict['char1_id'] = char1_id
                char2_code = row_dict.get('char2_code')
                char2_id = characteristic.get(char2_code)
                row_dict['char2_id'] = char2_id
            try:
                record = model(**row_dict)
            except (DatabaseError, ValueError, AttributeError, KeyError,
                    IntegrityError, Exception) as err:
                msg = 'Error when processing data import.\n' \
                    '- Worksheet name: {}\n' \
                    '- Row number: {}\n' \
                    '- Cell values: {}\n\n' \
                    '- Original Error:\n' + \
                    type(err).__name__ + ': ' + str(err)
                msg = msg.format(ws.name, i+1, row)
                logging.error(msg)
                raise PmaApiDbInteractionError(msg)

            db.session.add(record)

    db.session.commit()


def remove_stata_undefined_token_from_wb(wb: xlrd.book.Book):
    """Remove all instances of Stata undefined token '.' from wb

    Args:
        wb (xlrd.book.Book): workbook object

    Returns:
        xlrd.book.Book: Formatted workbook
    """
    numeric_types = (int, float, complex)
    field_types_to_format = (x.__name__ for x in numeric_types)
    book = copy(wb)
    sheet_names = [x for x in book.sheet_names()
                   if not str(x).startswith(IGNORE_SHEET_PREFIX)]
    data_sheet_names = [x for x in sheet_names
                        if str(x).startswith(DATA_SHEET_PREFIX)]
    sheets = [book.sheet_by_name(x) for x in data_sheet_names]

    # DEBUGGING
    # noinspection PyUnusedLocal
    none_in_field_vals = False
    # noinspection PyUnusedLocal
    empty_in_field_vals = False

    for sheet in sheets:
        for i in range(sheet.ncols):
            col = sheet.col(i)
            # field_name = col[0].value  # debugging

            field_vals = [x.value for x in col[1:] if x.value]
            sample_size = 50
            sample = field_vals[:sample_size]
            sample_types = [type(x).__name__ for x in sample]
            if len(sample_types) > 0:
                most_common_type = most_common(sample_types)
            else:
                most_common_type = None
            field_data_type = most_common_type

            # modify wb.sheet.col
            if field_data_type in field_types_to_format:
                for cell in col:
                    if cell.value == '.':
                        # TODO: Will this do the trick?
                        cell.value = None

            # DEBUGGING
            if None in field_vals:
                # noinspection PyUnusedLocal
                none_in_field_vals = True
            if '' in field_vals:
                # noinspection PyUnusedLocal
                empty_in_field_vals = True

    return book


def format_book(wb: xlrd.book.Book):
    """Format workbook by making edits to prevent edge case errors

    Args:
        wb (xlrd.book.Book): workbook object

    Returns:
        xlrd.book.Book: Formatted workbook
    """
    book = remove_stata_undefined_token_from_wb(wb)

    return book


def init_from_workbook(wb: str, queue: (),
                       progress_updater: TaskTracker = TaskTracker()):
    """Init from workbook.

    Args:
        wb (str): path to workbook file
        queue (tuple): Order in which to load db_models.
        progress_updater (TaskTracker): Tracks progress of task queue
    """
    with xlrd.open_workbook(wb) as book:
        book = format_book(book)

        # Init all structural metadata
        for sheetname_alias, model in queue:
            if sheetname_alias == 'data':
                continue
            progress_updater.next()
            sheetname: str = sheetname_alias
            ws = book.sheet_by_name(sheetname)
            init_from_sheet(ws, model)
        db.session.commit()

        # Init data
        init_data(wb=book,
                  progress_updater=progress_updater)

    # Init administrative metadata
    create_wb_metadata(wb)


def create_wb_metadata(wb_path):
    """Create metadata for Excel Workbook files imported into the DB.

    Args:
        wb_path (str) Path to Excel Workbook.
    """
    record = ApiMetadata(wb_path)
    db.session.add(record)
    db.session.commit()


def drop_tables(tables: Tuple[db.Model] = OVERWRITE_DROP_TABLES):
    """Drop database tables

    Side effects
        - Drops database tables

    Args:
        tables list(db.Model): Tables to drop

    Raises:
        OperationalError: If encounters such an error that is not 'database
        does not exist'
    """
    try:
        db.metadata.drop_all(db.engine, tables=tables)
    except OperationalError as err:
        if db_not_exist_tell not in str(err):
            raise err
        create_db()
        db.metadata.drop_all(db.engine, tables=tables)


def get_datasheet_names(path: str) -> List[str]:
    """Gets data sheet names from a workbook

    Args:
        path (str): Path to a workbook file

    Returns:
        list(str): List of datasheet names
    """
    with xlrd.open_workbook(path) as wb:
        data_sheets: List[xlrd.sheet] = \
            [x for x in wb.sheets() if x.name.startswith('data')]
        datasheet_names: List[str] = [x.name for x in data_sheets]

    return datasheet_names


def initdb_from_wb(
    _app: Flask = current_app,
    api_file_path: str = get_api_data(),
    ui_file_path: str = get_ui_data(),
    overwrite: bool = False,
    force: bool = False,
    callback=None) \
        -> dict:
    """Create the database.

    Args:
        _app (Flask): Flask application for context
        overwrite (bool): Overwrite database if True, else update.
        force (bool): Overwrite DB even if source data files present /
        supplied are same versions as those active in DB?'
        api_file_path (str): path to "API data file" spec xls file
        ui_file_path (str): path to "UIdata file" spec xls file
        callback: Callback function for progress yields

    Side effects:
        Always:
            - Creates tables
            - Adds values to database
            - Temporarily sets current dataset to 'processing'
            - Backs up database: at the beginning and end
        If overwrite:
            - Deletes all tables except for 'datasets'
            - Sets all other datasets to is_active=False

    Returns:
        dict: Results
    """
    retore_msg = 'An issue occurred. Restoring database to state it was in ' \
                 'prior to task initialization.'
    current_sub_tasks: List[str] = [
        'Backing up database'] + (
        ['Dropping tables'] if overwrite else []) + [
        'Creating tables'] + [
        'Uploading data for table: {}'
            .format(x[0]) for x in METADATA_MODEL_MAP] + [
        'Updating translations'] + [
        'Uploading data for table: {}'
            .format(x) for x in get_datasheet_names(api_file_path)] + [
        'Updating translations'
        'Creating cache',
        'Backing up resulting database']
    # tot_sub_tasks: int = len(current_sub_tasks)
    progress = TaskTracker(queue=current_sub_tasks,
                           callback=callback,
                           name='Initialize database'
                                '\n - Dataset: ' + api_file_path)
    api_dataset_already_active = False
    ui_dataset_already_active = False
    # TODO: Add this stuff to ProgressUpdater / TaskTracker
    warnings = {}
    status = {
        'success': False,
        'status': '',  # Current status message
        'current': 0.00,  # Percent completed
        'info': {
            'time_elapsed': None,
            'message': '',  # TODO: currently redundant
            'percent': 0,  # TODO: currently redundant
        },
        'warnings': warnings,
    }
    start_time = time()

    with _app.app_context():
        try:
            progress.next()
            try:
                backup_path: str = backup_db()
            except Exception as err:
                warnings['backup_1'] = str(err)

            # Delete all tables except for 'datasets'
            if overwrite:

                progress.next()
                drop_tables()
                Dataset.register_all_inactive()

            # Create tables
            progress.next()
            db.create_all()
            dataset, warning = Dataset.process_new(api_file_path)
            if warning:
                warnings['dataset'] = warning

            # Seed database
            if overwrite:
                # TODO: init_from_datasets_table if exists in db already?
                init_from_workbook(wb=api_file_path,
                                   queue=ORDERED_MODEL_MAP,
                                   progress_updater=progress)
                init_from_workbook(wb=ui_file_path,
                                   queue=TRANSLATION_MODEL_MAP,
                                   progress_updater=progress)

                progress.next()
                try:
                    Cache.cache_datalab_init(_app)
                except RuntimeError as err:
                    warnings['caching'] = caching_error.format(err)

            dataset.register_active()

            progress.next()
            try:
                backup_path: str = backup_db()
            except Exception as err:
                warnings['backup_2'] = str(err)

        except (OperationalError, AttributeError) as err:
            db.session.rollback()
            restore_db(backup_path)
            print(retore_msg)

            msg: str = str(err)
            if isinstance(err, OperationalError):
                msg: str = connection_error.format(str(err))
            elif isinstance(err, AttributeError):
                if env_access_err_tell in str(err):
                    msg: str = env_access_err_msg\
                        .format(type(err).__name__ + ': ' + str(err))
            raise PmaApiDbInteractionError(msg)

        # noinspection PyTypeChecker
        seconds_elapsed = str(int(time() - start_time)) + ' seconds'
        status['info']['time_elapsed'] = seconds_elapsed
        status['success'] = True
        status['current'] = 1
        status['status'] = 'Finished'

        progress.complete()

        return status


def load_data_file(filepath: str):
    """Load data file into memory

    Args:
        filepath (str): Path of file to load into memory

    Returns:
        xlrd.Book: workbook file object
    """
    wb = xlrd.open_workbook(filepath)

    return wb


# TODO - Haven't validated anything yet, 2019-01-17 jef
# noinspection PyUnusedLocal
def validate_data_file(file: xlrd.Book = None, filepath: str = ''):
    """Validate data file

    Args:
        file (xlrd.Book): Validate Workbook obj
        filepath (str): Validate Workbook file at path

    Raises:
        InvalidDataFileError: if file is not valid
    """
    valid = True
    filename = '' if not filepath else ntpath.basename(filepath)
    filename_placeholder = 'with name {}'.format(filename)
    if not valid:
        msg = 'File {} was not a valid data file.'.format(filename_placeholder)
        raise InvalidDataFileError(msg)


def write_data_file_to_db(filepath: str):
    """Load, validate, and commit data file to db

    Args:
        filepath (str) Path of file to write

    Raises:
        - See: validate_data_file()

    Side effects:
        - See: commit_data_file()
    """
    file = load_data_file(filepath)
    validate_data_file(file, filepath)
    commit_data_file(file)
    create_wb_metadata(filepath)


def commit_data_file(file: xlrd.Book):
    """Write data file to db

    Args:
        file (xlrd.Book): workbook file to write to db

    Side effects:
        Writes data to db.
        - See: process_metadata(), process_data(), process_translations()
    """
    process_metadata(file)
    process_data(file)
    process_translations(file)


# TODO - 2019-01-17 jef
# noinspection PyUnusedLocal
def process_translations(file: xlrd.Book):
    """Read and write translations from xlrd.Book into db
    
    Args:
        file (xlrd.Book): contains contents to write

    Side effects:
        Writes data to db. 
    """
    # read
    # noinspection PyUnusedLocal
    for item in TRANSLATION_MODEL_MAP:
        pass

    # write
    pass


def process_metadata(file: xlrd.Book):
    """Read and write data from xlrd.Book into db

    Args:
        file (xlrd.Book): contains contents to write

    Side effects:
        Writes data to db.
    """
    sheets_present = file.sheet_names()
    # read & write
    for sheetname, model in ORDERED_MODEL_MAP:
        if sheetname in sheets_present:
            ws = file.sheet_by_name(sheetname)
            init_from_sheet(ws, model)


def process_data(file: xlrd.Book):
    """Read and write metadata from xlrd.Book into db

    Args:
        file (xlrd.Book): contains contents to write

    Side effects:
        Writes data to db.
    """
    # read & write
    init_data(file)


def new_backup_path(ext: str = 'dump') -> str:
    """Backup default path

    Args:
        ext (str): File extension to use

    Returns:
        str: Default path of backup file at specific date and time
    """
    import platform

    filename_base = 'pma-api-backup'
    datetime_str: \
        str = str(datetime.now()).replace('/', '-').replace(':', '-')\
        .replace(' ', '_')
    op_sys = 'MacOS' if platform.system() == 'Darwin' else platform.system()
    env: str = os.getenv('ENV_NAME', 'development')
    filename: str = '_'.join(
        [filename_base, op_sys, env, datetime_str]
    ) + '.' + ext

    return os.path.join(BACKUPS_DIR, filename)


def grant_full_permissions_to_file(path):
    """Grant access to file

    Raises:
        PmaApiException: If errors during process
    """
    cmd: List[str] = 'chmod 600 {}'\
        .format(path)\
        .split(' ')
    output: Dict = run_proc(cmd)
    errors: str = output['stderr']

    if errors:
        raise PmaApiException(errors)


def update_pgpass(creds: str, path: str = os.path.expanduser('~/.pgpass')):
    """Update pgpass file with credentials

    Side effects:
        - Updates file
        - Creates file if does not exist

    Args:
        creds (str): Url pattern string containing connection credentials
        path (str): Path to pgpass file
    """
    cred_line: str = creds if creds.endswith('\n') else creds + '\n'

    with open(path, 'r') as file:
        contents: str = file.read()
        exists: bool = creds in contents
        cred_line = cred_line if contents.endswith('\n') else cred_line + '\n'
    if not exists:
        with open(path, 'a+') as file:
            file.write(cred_line)


def backup_local_using_heroku_postgres(path: str = new_backup_path(),
                                       app_name: str = APP_NAME) \
        -> str:
    """Backup using Heroku PostgreSQL DB using Heroku CLI

    Args:
        path (str): Path of file to save
        app_name (str): Name of app as recognized by Heroku

    Side effects:
        - Runs command: `heroku pg:backups:capture`
        - Runs command: `heroku pg:backups:download`
        - Downloads to file system
        - Makes directory (if not exist)

    Raises:
        PmaApiDbInteractionError: If errors during process

    Returns:
        str: path to backup file saved
    """
    target_dir = os.path.dirname(path) if path else BACKUPS_DIR
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    cmd_str_base: str = \
        'heroku pg:backups:capture --app={app}'
    cmd_str: str = cmd_str_base.format(app=app_name)
    run_proc(cmd=cmd_str, raises=False, prints=True)

    cmd_str_base2: str = \
        'heroku pg:backups:download --app={app} --output={output}'
    cmd_str2: str = cmd_str_base2.format(app=app_name, output=path)
    run_proc(cmd_str2, raises=False, prints=True)

    return path


def backup_using_pgdump(path: str = new_backup_path(ext = 'dump')) -> str:
    """Backup using pg_dump

    Args:
        path (str): Path of file to save

    Side effects:
        - Grants full permissions to .pgpass file
        - Reads and writes to .pgpass file
        - Runs pg_dump process, storing result to file system

    Raises:
        PmaApiDbInteractionError: If errors during process

    Returns:
        str: path to backup file saved
    """
    pgpass_url_base = '{hostname}:{port}:{database}:{username}:{password}'
    pgpass_url: str = pgpass_url_base.format(**db_connection_info)
    pgpass_path = os.path.expanduser('~/.pgpass')
    grant_full_permissions_to_file(pgpass_path)
    update_pgpass(path=pgpass_path, creds=pgpass_url)

    cmd_base: str = \
        'pg_dump --format=custom --host={hostname} --port={port} ' \
        '--username={username} --dbname={database} --file {path}'
    cmd: str = cmd_base.format(**db_connection_info, path=path)
    output: Dict = run_proc(cmd)

    errors: str = output['stderr']
    if errors:
        with open(os.path.expanduser('~/.pgpass'), 'r') as file:
            pgpass_contents: str = file.read()
        msg = '\n' + errors + \
            'Offending command: ' + cmd + \
            'Pgpass contents: ' + pgpass_contents
        raise PmaApiDbInteractionError(msg)

    return path


def backup_local(path: str = '') -> str:
    """Backup database locally

    Args:
        path (str): Path to save file

    Side effects:
        - Saves file at path

    Raises:
        PmaApiDbInteractionError: If DB exists and any errors during backup

    Returns:
        str: Path to backup file saved
    """
    target_dir = os.path.dirname(path) if path else BACKUPS_DIR

    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    try:
        if os.getenv('ENV_NAME') == 'development':
            saved_path: str = backup_using_pgdump(path) if path \
                else backup_using_pgdump()
        else:
            saved_path: str = backup_local_using_heroku_postgres(path) if path \
                else backup_local_using_heroku_postgres()
        return saved_path
    except PmaApiDbInteractionError as err:
        if db_not_exist_tell not in str(err):
            raise err


@aws_s3
def store_file_on_s3(path: str, storage_dir: str = ''):
    """Given path to file on local file system, push file to AWS S3

    Prerequisites:
        Environmental variable setup: https://boto3.amazonaws.com/v1/
    documentation/api/latest/guide/quickstart.html#configuration

    Side effects:
        - Uploads to cloud

    Args:
        path (str): Path to local file
        storage_dir (str): Subdirectory path where file should be stored

    Returns:
        str: File name of uploaded file
    """
    import boto3

    local_backup_first = False if os.path.exists(path) else True
    filename = ntpath.basename(path)

    s3 = boto3.resource(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

    if local_backup_first:
        backup_local(path)
    with open(path, 'rb') as f:
        filepath = storage_dir + filename
        s3.Bucket(BUCKET).put_object(Key=filepath, Body=f)
    if local_backup_first:
        os.remove(path)

    return filename


def backup_ui_data(path: str = get_ui_data()) -> str:
    """Given path to file on local file system, push file to AWS S3

    Args:
        path (str): Path to local file

    Returns:
        str: File name of uploaded file
    """
    filename: str = store_file_on_s3(path=path,
                                     storage_dir=S3_UI_DATA_DIR_PATH)

    return filename


def backup_datasets(path: str = get_api_data()) -> str:
    """Given path to file on local file system, push file to AWS S3

    Args:
        path (str): Path to local file

    Returns:
        str: File name of uploaded file
    """
    filename: str = store_file_on_s3(path=path,
                                     storage_dir=S3_DATASETS_DIR_PATH)

    return filename


def backup_source_files():
    """Backup ui data and datasets"""
    backup_ui_data()
    backup_datasets()


def backup_db_cloud(path_or_filename: str = ''):
    """Backs up database to the cloud

    If path_or_filename is a path, uploads from already stored backup at path.
    Else if it is a path_or_filename, creates new backup and then uploads that.

    Args:
        path_or_filename (str): Either path to a backup file, or file name. If
        file name, will restore from local backup if file exists in default
        backups directory, else will restore from the cloud.

    Side effects:
        - backup_local()
        - backup_to_s3()
    """
    if not path_or_filename:
        path = new_backup_path()
    else:
        pth = os.path.split(path_or_filename)
        is_filename = len(pth) < 2 or (len(pth) == 2 and pth[0])
        path = path_or_filename if not is_filename \
            else os.path.join(BACKUPS_DIR, path_or_filename)

    local_backup_first = False if os.path.exists(path) else True

    if local_backup_first:
        backup_local(path)
    filename: str = store_file_on_s3(
        path=path,
        storage_dir=S3_BACKUPS_DIR_PATH)
    if local_backup_first:
        os.remove(path)

    return filename


def backup_db(path: str = ''):
    """Backup database locally and to the cloud

    Args:
        path (str): Path to save file

    Side effects:
        - backup_local()
        - backup_cloud()

    Returns:
        str: Path saved locally
    """
    saved_path: str = backup_local(path)
    backup_db_cloud(saved_path)

    return saved_path


# TODO
def restore_using_heroku_postgres(s3_signed_url: str = '', db_url: str = '',
                                  app_name: str = APP_NAME):
    """Restore Heroku PostgreSQL DB using Heroku CLI

    Args:
        s3_signed_url (str): AWS S3 presigned object url  TODO: currently
         unsigned)
        db_url (str): Heroku DB 'COLOR' url  TODO: currently normal DB url
        app_name (str): Name of app as recognized by Heroku

    Side effects:
        - Restores database
        - Drops any tables and other database objects before recreating them
    """
    # dl_url: str = s3_signed_url if s3_signed_url else '?'
    # upload_url = db_url if db_url else '?'
    dl_url = s3_signed_url
    upload_url = db_url

    cmd_str_base: str = \
        "heroku pg:backups:restore '{s3_signed_url}' {db_url} --app={app}"
    cmd_str: str = cmd_str_base.format(
        s3_signed_url=dl_url,
        db_url=upload_url,
        app=app_name)
    run_proc(cmd_str)

    # 1: aws s3 presign s3://your-bucket-address/your-object
    #
    # 2: DATABASE_URL represents the HEROKU_POSTGRESQL_COLOR_URL of the db
    # you wish to restore to. You must specify a database configuration
    # variable to restore the database.


def restore_using_pgrestore(path: str, dropdb: bool = False):
    """Restore postgres datagbase using pg_restore

    Args:
        path (str): Path of file to restore
        dropdb (bool): Drop database in process?

    Side effects:
        - Restores database
        - Drops database (if dropdb)
    """
    cmd_base: str = 'pg_restore --exit-on-error --create {drop}' \
                    '--dbname={database} --host={hostname} --port={port} ' \
                    '--username={username} {path}'

    cmd_str: str = cmd_base.format(
        **root_connection_info,
        path=path,
        drop='--clean ' if dropdb else '')
    cmd: List[str] = cmd_str.split(' ')

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)
    try:
        for line in iter(proc.stdout.readline, ''):
            print(line.encode('utf-8'))
    except AttributeError:
        print(proc.stdout)

    errors = proc.stderr.read()
    if errors:
        msg = '\n' + errors + \
            'Offending command: ' + cmd_str
        log_process_stderr(msg, err_msg=db_mgmt_err)
        raise PmaApiDbInteractionError(msg)

    proc.stderr.close()
    proc.stdout.close()
    proc.wait()


def superuser_dbms_connection(
        connection_url: str = os.getenv('DBMS_SUPERUSER_URL')) -> Connection:
    """Connect to database management system as a super user

    Returns:
        sqlalchemy.engine.Connection: connection object
    """
    from sqlalchemy import create_engine

    engine_default = create_engine(connection_url)
    conn: sqlalchemy.engine.Connection = engine_default.connect()

    return conn


def view_db_connections() -> List[dict]:
    """View active connections to a db

    Returns:
        list(dict): List of active connections in the form of dictionaries
        containing information about connections
    """
    # noinspection PyProtectedMember
    from sqlalchemy.engine import ResultProxy

    try:
        db_name: str = current_app.config.get('DB_NAME', 'pmaapi')
    except RuntimeError as err:
        if 'Working outside of application context' not in str(err):
            raise err
        db_name: str = 'pmaapi'
    statement = "SELECT * FROM pg_stat_activity WHERE datname = '%s'" \
                % db_name
    conn: Connection = superuser_dbms_connection()

    conn.execute("COMMIT")
    result: ResultProxy = conn.execute(statement)
    conn.close()

    active_connections: List[dict] = []
    for row in result:
        conn_info = {}
        for key_val in row.items():
            conn_info = {**conn_info, **{key_val[0]: key_val[1]}}
        active_connections.append(conn_info)

    return active_connections


def create_db(name: str = 'pmaapi', with_schema: bool = True):
    """Create a brand new database

    Side effects:
        - Creates database
        - Creates database tables and schema (if with_schema)

    Args:
        name (str): Name of database to create
        with_schema (bool): Also create all tables and initialize them?
    """
    db_name: str = current_app.config.get('DB_NAME', name)
    conn: Connection = superuser_dbms_connection()

    conn.execute("COMMIT")
    conn.execute("CREATE DATABASE %s" % db_name)
    conn.close()

    if with_schema:
        db.create_all()


# def drop_db(db_name: str = Config.DB_NAME, hard: bool = False):
#     """Drop database
#
#     Side effects:
#         - Drops database
#         - Kills active connections (if 'hard')
#
#     Args:
#         db_name (str): Database name
#         hard (bool): Kill any active connections?
#     """
#     import signal
#
#     if hard:
#         connections: List[dict] = view_db_connections()
#         process_ids: List[int] = [x['pid'] for x in connections]
#         for pid in process_ids:
#             os.kill(pid, signal.SIGTERM)
#
#     cmd_str: str = 'dropdb {}'.format(db_name)
#     cmd: List[str] = cmd_str.split(' ')
#
#     proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
#                             stderr=subprocess.PIPE,
#                             universal_newlines=True)
#
#     try:
#         for line in iter(proc.stdout.readline, ''):
#             print(line.encode('utf-8'))
#     except AttributeError:
#         print(proc.stdout)
#
#     errors = proc.stderr.read()
#     if errors:
#         db_exists = False if db_not_exist_tell in errors else True
#         if db_exists:
#             msg = '\n' + errors + \
#                 'Offending command: ' + cmd_str
#             log_process_stderr(msg, err_msg=db_mgmt_err)
#             raise PmaApiDbInteractionError(msg)
#
#     proc.stderr.close()
#     proc.stdout.close()
#     proc.wait()
#
#
@aws_s3
def download_file_from_s3(filename: str, directory: str):
    """Download a file from AWS S3

    Args:
        filename (str): Name of file to restore
        directory (str): Path to directory to store file

    Returns:
        str: path to downloaded file
    """
    import boto3
    from botocore.exceptions import ClientError

    s3 = boto3.resource('s3')
    download_to_path: str = S3_BACKUPS_DIR_PATH + filename
    download_from_path: str = os.path.join(directory, filename)

    try:
        s3.Bucket(BUCKET).download_file(download_to_path, download_from_path)
    except ClientError as err:
        msg = 'The file requested was not found on AWS S3.\n' \
            if err.response['Error']['Code'] == '404' \
            else 'An error occurred while trying to download from AWS S3.\n'
        msg += '- File requested: ' + filename
        raise PmaApiDbInteractionError(msg)

    return download_from_path


@aws_s3
def list_s3_objects(bucket_name: str = BUCKET) -> []:
    """List objects on AWS S3

    Args:
        bucket_name (str): Name of bucket holding object storage

    Returns:
        list: List of S3 objects
    """
    import boto3

    s3 = boto3.resource('s3')
    objects = s3.Bucket(bucket_name).objects.all()

    return [x.key for x in objects]


def list_filtered_s3_files(path: str) -> []:
    """Gets list of S3 files w/ directories and path prefixes filtered out

    Args:
        path (str): Path to directory holding files

    Returns:
        list: Filenames
    """
    path2 = path + '/' if not path.endswith('/') else path
    path3 = path2[1:] if path2.startswith('/') else path2
    objects = list_s3_objects(silent=True)

    filtered = [x for x in objects
                if x.startswith(path3)
                and x != path3]
    formatted = [os.path.basename(x) for x in filtered]

    return formatted


def list_cloud_backups() -> [str]:
    """List available cloud backups

    Returns:
        list: backups
    """
    files = list_filtered_s3_files(S3_BACKUPS_DIR_PATH)

    return files


def list_cloud_ui_data() -> [str]:
    """List ui data spec files on AWS S3

    Returns:
        list: List of files
    """
    files = list_filtered_s3_files(S3_UI_DATA_DIR_PATH)

    return files


def list_cloud_datasets() -> [str]:
    """List pma api dataset spec files on AWS S3

    Returns:
        list: List of files
    """
    files = list_filtered_s3_files(S3_DATASETS_DIR_PATH)

    return files


def list_local_files(path: str, name_contains: str = '') -> [str]:
    """List applicable files in directory

    Args:
        path (str): Path to a directory containing files
        name_contains (str): Additional filter to discard any files that do not
        contain this string

    Returns:
        list: files
    """
    try:
        all_files = os.listdir(path)
    except FileNotFoundError:
        msg = 'Path \'{}\' does not appear to exist.'.format(path)
        raise PmaApiException(msg)

    filenames = [x for x in all_files
                 if x not in FILE_LIST_IGNORES
                 and not os.path.isdir(os.path.join(path, x))]
    filenames = [x for x in filenames if name_contains in x] if name_contains \
        else filenames

    return filenames


def list_local_datasets(path: str = DATASETS_DIR) -> [str]:
    """List available local datasets

    Args:
        path (str): Path to datasets directory

    Returns:
        list: datasets
    """
    from_file_system: List[str] = \
        list_local_files(path=path, name_contains='api_data')
    from_db: [str] = [x.dataset_display_name for x in Dataset.query.all()]
    filenames: [str] = list(set(from_file_system + from_db))

    return filenames


def list_local_ui_data(path: str = UI_DATA_DIR) -> [str]:
    """List available local backups

    Args:
        path (str): Path to backups directory

    Returns:
        list: backups
    """
    filenames = list_local_files(path=path, name_contains='ui_data')

    return filenames


def list_local_backups(path: str = BACKUPS_DIR) -> [str]:
    """List available local backups

    Args:
        path (str): Path to backups directory

    Returns:
        list: backups
    """
    filenames = list_local_files(path=path)

    return filenames


def list_backups() -> {str: [str]}:
    """List available backups

    Returns:
        dict: available backups, of form...
        {'local': [...], 'cloud': [...]
    """
    return {
        'local': list_local_backups(),
        'cloud': list_cloud_backups()
    }


def list_ui_data() -> {str: [str]}:
    """List available ui data spec files

    Returns:
        dict: available backups, of form...
        {'local': [...], 'cloud': [...]
    """
    return {
        'local': list_local_ui_data(),
        'cloud': list_cloud_ui_data()
    }


def list_datasets() -> {str: [str]}:
    """List available api data spec files

    Returns:
        dict: available backups, of form...
        {'local': [...], 'cloud': [...]
    """
    return {
        'local': list_local_datasets(),
        'cloud': list_cloud_datasets()
    }


def restore_db_cloud(filename: str):
    """Restore database

    Args:
        filename (str): Name of file to restore

    Side effects:
        Reverts database to state of backup file
    """
    if os.getenv('ENV_NAME') == 'development':
        path: str = download_file_from_s3(filename=filename,
                                          directory=BACKUPS_DIR)
        restore_db_local(path)
    else:
        # TODO: make same as test file
        dl_path: str = os.path.join(BACKUPS_DIR, filename)
        dl_url_base = 'https://{bucket}.s3.amazonaws.com/{key}'
        dl_url = dl_url_base.format(bucket=BUCKET, key=dl_path)

        db_url = os.getenv('DATABASE_URL')

        restore_using_heroku_postgres(s3_signed_url=dl_url, db_url=db_url)


def restore_db(path_or_filename: str):
    """Restore database

    Args:
        path_or_filename (str): Either path to a backup file, or file name. If
        file name, will restore from local backup if file exists in default
        backups directory, else will restore from the cloud.

    Side effects:
        Reverts database to state of backup file
    """
    dirpath, filename = os.path.split(path_or_filename)

    local_path = os.path.join(BACKUPS_DIR, filename) if not dirpath \
        else path_or_filename
    if os.path.exists(local_path):
        restore_db_local(local_path)
    else:
        restore_db_cloud(filename)


def restore_db_local(path: str):
    """Restore database

    Args:
        path (str): Path to backup file

    Side effects:
        Reverts database to state of backup file
    """
    err_msg = '\n\nAn error occurred while trying to restore db from file: {}'\
        '.In the process of db restoration, a last-minute backup of db' \
        ' was created: {}. If you are seeing this message, then this ' \
        'last-minute backup should have already been restored. However' \
        ', if it appears that your db has been dropped, you may restore'\
        ' from this file manually.\n\n' \
        '- Original error: \n{}'
    emergency_backup = new_backup_path()

    backup_local(emergency_backup)

    if os.path.getsize(emergency_backup) == 0:  # no db existed
        os.remove(emergency_backup)

    # noinspection PyBroadException
    # drop_db(hard=True)

    try:
        restore_using_pgrestore(path=path, dropdb=True)
    except Exception as err:
        if os.path.exists(emergency_backup):
            restore_using_pgrestore(path=emergency_backup, dropdb=True)
            err_msg = err_msg.format(path, emergency_backup, str(err))
            raise PmaApiDbInteractionError(err_msg)
        else:
            raise err

    if os.path.exists(emergency_backup):
        os.remove(emergency_backup)


@aws_s3
def delete_s3_file(filename: str):
    """Delete a file from AWS S3

    Args:
        filename (str): Name of file

    Side effects:
        - deletes file
    """
    import boto3

    s3 = boto3.resource('s3')
    s3.Object(BUCKET, filename).delete()

"""Database management"""
import csv
import glob
import logging
import ntpath
import os
import subprocess
from collections import OrderedDict
from copy import copy
from datetime import datetime
from typing import List, Dict, Union, Iterable

import boto3
import xlrd
from xlrd.sheet import Sheet
from xlrd.book import Book
import sqlalchemy
from flask import Flask, current_app
from flask_user import UserManager
from sqlalchemy import Table
# noinspection PyProtectedMember
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError, IntegrityError, DatabaseError

from pma_api import create_app
from pma_api.config import DATA_DIR, BACKUPS_DIR, Config, \
    IGNORE_SHEET_PREFIX, DATA_SHEET_PREFIX, AWS_S3_STORAGE_BUCKETNAME as \
    BUCKET, S3_BACKUPS_DIR_PATH, S3_DATASETS_DIR_PATH, S3_UI_DATA_DIR_PATH, \
    UI_DATA_DIR, DATASETS_DIR, API_DATASET_FILE_PREFIX as API_PREFIX, \
    UI_DATASET_FILE_PREFIX as UI_PREFIX, HEROKU_INSTANCE_APP_NAME as APP_NAME,\
    FILE_LIST_IGNORES, TEMP_DIR
from pma_api.error import PmaApiDbInteractionError, PmaApiException
from pma_api.models import db, Cache, Characteristic, CharacteristicGroup, \
    Task, Country, Data, EnglishString, Geography, Indicator, ApiMetadata, \
    Survey, Translation, Dataset, User
from pma_api.utils import most_common
from pma_api.manage.utils import log_process_stderr, run_proc, \
    _get_bin_path_from_ref_config

# Sorted in order should be executed
ORDERED_METADATA_SHEET_MODEL_MAP = OrderedDict({  # str,db.Model
    'geography': Geography,
    'country': Country,
    'survey': Survey,
    'char_grp': CharacteristicGroup,
    'char': Characteristic,
    'indicator': Indicator
})
# For lookup
DATASET_WB_SHEET_MODEL_MAP = {
    **ORDERED_METADATA_SHEET_MODEL_MAP,
    **{'data': Data},
    **{'translation': Translation}}
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
            else:
                # TODO: suppression works when running tests in Pycharm,
                #  but running `make backup` from terminal hangs
                # S3 has unfixed resource warnings
                # with SuppressStdoutStderr():
                #     return func(*args, **wrapper_kwargs_removed)
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
    return dict(
        app=create_app(os.getenv('ENV_NAME', 'default')), db=db,
        Country=Country, EnglishString=EnglishString, Translation=Translation,
        Survey=Survey, Indicator=Indicator, Data=Data, Task=Task, User=User,
        Characteristic=Characteristic, Cache=Cache, ApiMetadata=ApiMetadata,
        CharacteristicGroup=CharacteristicGroup, Dataset=Dataset,
        Geography=Geography)


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

    # For de-bug purposes
    # noinspection PyUnusedLocal
    none_in_field_vals = False
    # noinspection PyUnusedLocal
    empty_in_field_vals = False

    for sheet in sheets:
        for i in range(sheet.ncols):
            col = sheet.col(i)
            # field_name = col[0].value  # For de-bug

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

            # For de-bug purposes
            if None in field_vals:
                # noinspection PyUnusedLocal
                none_in_field_vals = True
            if '' in field_vals:
                # noinspection PyUnusedLocal
                empty_in_field_vals = True

    return book


def commit_from_sheet(ws: Sheet, model: db.Model, **kwargs):
    """Initialize DB table data from XLRD Worksheet.

    Initialize table data from source data associated with corresponding
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
                msg = msg.format(ws.name, i + 1, row)
                logging.error(msg)
                raise PmaApiDbInteractionError(msg)

            db.session.add(record)

    # TODO: After adding FunctionalTask class, is this necessary?
    # TODO 2019.04.08-jef: This is really not ideal. This exists here because
    #  every model creates new EnglishString records, and given how we
    #  currently create and generate unique codes, it appears we /may/ need to
    #  commit both the original record and the english string record. So,
    #  for such models, everything will have already been committed, hence
    #  why we currently run this additional 'commit_needed' step/check.
    # sheet_rows: int = ws.nrows - 1
    # db_rows: int = len(model.query.all())
    # commit_needed: bool = db_rows < sheet_rows
    # if commit_needed:
    #     db.session.commit()


def format_book(wb: Book) -> Book:
    """Format workbook by making edits to prevent edge case errors

    Args:
        wb (xlrd.book.Book): workbook object

    Returns:
        xlrd.book.Book: Formatted workbook
    """
    book: Book = remove_stata_undefined_token_from_wb(wb)

    return book


def register_administrative_metadata(wb_path):
    """Create metadata for Excel Workbook files imported into the DB.

    Args:
        wb_path (str) Path to Excel Workbook.
    """
    record = ApiMetadata(wb_path)
    db.session.add(record)
    db.session.commit()


def drop_tables(tables: Iterable[Table] = None):
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
        if tables:
            db.metadata.drop_all(db.engine, tables=tables)
        else:
            db.drop_all()
    except OperationalError as err:
        if db_not_exist_tell not in str(err):
            raise err
        create_db()
        if tables:
            db.metadata.drop_all(db.engine, tables=tables)
        else:
            db.drop_all()


def get_datasheet_names(wb: Book) -> List[str]:
    """Gets data sheet names from a workbook

    Args:
        wb (Book): Pre-loaded XLRD Workbook obj

    Returns:
        list(str): List of datasheet names
    """
    data_sheets: List[xlrd.sheet] = \
        [x for x in wb.sheets() if x.name.startswith('data')]
    datasheet_names: List[str] = [x.name for x in data_sheets]

    return datasheet_names


def is_db_empty(_app: Flask = current_app) -> bool:
    """Is database empty or not?

    Empty is defined here as a DB that has been created, but has no tables. As
    a proxy for this ideal way of telling if DB is empty, this function
    currently just checks if there is any data in the 'data' table.

    Args:
        _app (Flask): Flask application for context

    Returns:
        bool: True if empty, else False
    """
    with _app.app_context():
        data_present: Data = Data.query.first()
        empty: bool = not data_present

    return empty


def new_backup_path(_os: str = '', _env: str = '', ext: str = 'dump') -> str:
    """Backup default path

    Args:
        _os (str): Operating system backup is being created on. Useful to add
        this if backing up remotely. Otherwise, backup name will
        reflect the OS of current system.
        _env (str): Environment name where backup is being created. Useful to
        add  if backing up remotely. Otherwise, backup name will
        reflect the environment of current system.
        ext (str): File extension to use

    Returns:
        str: Default path of backup file at specific date and time
    """
    import platform

    filename_base = 'pma-api-backup'
    datetime_str: \
        str = str(datetime.now()).replace('/', '-').replace(':', '-')\
        .replace(' ', '_')
    if not _os:
        op_sys: str = \
            'MacOS' if platform.system() == 'Darwin' else platform.system()
    else:
        op_sys: str = _os
    if not _env:
        env: str = os.getenv('ENV_NAME', 'development')
    else:
        env: str = _env
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


def backup_local_using_heroku_postgres(
        path: str = new_backup_path(),
        app_name: str = APP_NAME,
        silent: bool = False) -> str:
    """Backup using Heroku PostgreSQL DB using Heroku CLI

    Args:
        path (str): Path of file to save
        app_name (str): Name of app as recognized by Heroku
        silent (bool): Don't print updates?

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
    run_proc(cmd=cmd_str, raises=False, prints=not silent)

    cmd_str_base2: str = \
        'heroku pg:backups:download --app={app} --output={output}'
    cmd_str2: str = cmd_str_base2.format(app=app_name, output=path)
    run_proc(cmd_str2, raises=False, prints=not silent)

    return path


def backup_using_pgdump(path: str = new_backup_path()) -> str:
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


def backup_local(path: str = '', silent: bool = False) -> str:
    """Backup database locally

    Args:
        path (str): Path to save file
        silent (bool): Don't print updates?

    Side effects:
        - Saves file at path

    Raises:
        PmaApiDbInteractionError: If DB exists and any errors during backup

    Returns:
        str: Path to backup file saved
    """
    func = backup_local_using_heroku_postgres
    target_dir = os.path.dirname(path) if path else BACKUPS_DIR

    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    try:
        if os.getenv('ENV_NAME') == 'development':
            saved_path: str = backup_using_pgdump(path) if path \
                else backup_using_pgdump()
        else:
            saved_path: str = func(path=path, silent=silent) if path \
                else func(silent=silent)
        return saved_path
    except PmaApiDbInteractionError as err:
        if db_not_exist_tell not in str(err):
            raise err


@aws_s3
def store_file_on_s3(path: str, storage_dir: str = ''):
    """Given path to file on local file system, upload file to AWS S3

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
    local_backup_first = False if os.path.exists(path) else True
    filename = ntpath.basename(path)

    s3 = boto3.resource(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

    if local_backup_first:
        backup_local(path)

    # Datasets only: This only applies to datasets, so might want refactor.
    # noinspection PyBroadException
    try:
        metadata: Dict[str, str] = {}
        d = Dataset(path)
        metadata['dataset_display_name']: str = d.dataset_display_name
        metadata['version_number']: str = str(d.version_number)
        metadata['dataset_type']: str = d.dataset_type
    except Exception:
        metadata: Dict[str, str] = {}

    # TODO Troubleshoot slow upload: https://github.com/boto/boto3/issues/409
    #  Until fixed, print these statements.
    #  Experiments (seconds): 62, 61, 104, 68, 59, 58, 0, 65
    msg1 = 'Backing up to cloud: {}'.format(filename) + \
           '\nThis normally takes seconds, but due to intermittent issues ' \
           'with Amazon Web Services S3 file storage service, this has known '\
           'to occasionally take between 1-2 minutes.'
    msg2 = 'Backup of file complete. Seconds elapsed: {}'
    with open(path, 'rb') as f:
        filepath = storage_dir + filename
        print(msg1)
        t1 = datetime.now()
        s3.Bucket(BUCKET).put_object(
            Key=filepath,
            Metadata=metadata,
            Body=f)
        t2 = datetime.now()
        elapsed_seconds: int = int((t2 - t1).total_seconds())
        print(msg2.format(elapsed_seconds))
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


def backup_db_cloud(path_or_filename: str = '', silent: bool = False):
    """Backs up database to the cloud

    If path_or_filename is a path, uploads from already stored backup at path.
    Else if it is a path_or_filename, creates new backup and then uploads that.

    Args:
        path_or_filename (str): Either path to a backup file, or file name. If
        file name, will restore from local backup if file exists in default
        backups directory, else will restore from the cloud.
        silent (bool): Don't print updates?

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
        backup_local(path=path, silent=silent)
    filename: str = \
        store_file_on_s3(path=path, storage_dir=S3_BACKUPS_DIR_PATH)
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


def s3_signed_url(url: str, sleep: int = 1) -> str:
    """From an unsigned AWS S3 object URL, generates and returns signed one.

    Args:
        url (str): Unsigned AWS S3 object URL
        sleep (int): Amount of time, in seconds,  to sleep after creating URL.
        Useful for combining with another operation which will use generated
        URL.

    Returns:
        str: Signed AWS S3 URL for object
    """
    import time

    bucket, key = url.replace('https://', '').split('.s3.amazonaws.com/')
    s3 = boto3.client('s3')
    signed_url: str = s3.generate_presigned_url(
        ClientMethod='get_object',
        ExpiresIn=7 * 24 * 60 * 60,  # 7 days; maximum
        Params={
            'Bucket': bucket,
            'Key': key
        }
    )

    time.sleep(sleep)

    return signed_url


def restore_using_heroku_postgres(
        s3_url: str = '',
        s3_url_is_signed: bool = False,
        app_name: str = APP_NAME,
        silent: bool = False,
        ok_tells: tuple = ('Restoring... done',)):
    """Restore Heroku PostgreSQL DB using Heroku CLI

    Args:
        s3_url (str): AWS S3 unsigned object url. If signed, should pass
        's3_url_is_signed' param as True.
        s3_url_is_signed (bool): Is this a S3 signed url? If not, will attempt
        to sign before doing restore.
        app_name (str): Name of app as recognized by Heroku
        silent (bool): Don't print updates?
        ok_tells (tuple(str)): A list of strings to look for in the command
        result output. If any given 'tell' strings are in the output, we will
        consider the result to be ok. It is important to note that if using a
        different version of the Heroku CLI, it is possible that the output
        will appear to be different. If so, try to find another 'ok tell'
        inside the output, and add it to the list.

    Side effects:
        - Signs url if needed
        - Restores database
        - Drops any tables and other database objects before recreating them
    """
    signed_url: str = s3_url if s3_url_is_signed else s3_signed_url(s3_url)

    cmd_str_base: str = \
        'heroku pg:backups:restore "{s3_url}" DATABASE_URL ' \
        '--confirm {app} --app {app}'
    cmd_str: str = cmd_str_base.format(
        s3_url=signed_url,
        app=app_name)

    output: Dict[str, str] = run_proc(
        cmd=cmd_str,
        prints=not silent,
        raises=False)

    possible_err = output['stderr']
    apparent_success = not possible_err or \
        any(x in possible_err for x in ok_tells)
    if not apparent_success:
        msg = '\n' + possible_err + \
              'Offending command: ' + str(cmd_str)
        raise PmaApiDbInteractionError(msg)


def restore_using_pgrestore(
        path: str, attempt: int = 1, dropdb: bool = False,
        silent: bool = False):
    """Restore postgres datagbase using pg_restore

    Args:
        path (str): Path of file to restore
        attempt (int): Attempt number
        dropdb (bool): Drop database in process?
        silent (bool): Don't print updates?

    Side effects:
        - Restores database
        - Drops database (if dropdb)
    """
    system_bin_paths: List[str] = \
        ['pg_restore', '/usr/local/bin/pg_restore']
    system_bin_path_registered: str = \
        _get_bin_path_from_ref_config(bin_name='pg_restore', system=True)
    if system_bin_path_registered not in system_bin_paths:
        system_bin_paths.append(system_bin_path_registered)
    project_bin_path: str = \
        _get_bin_path_from_ref_config(bin_name='pg_restore', project=True)
    pg_restore_paths: List[str] = []
    if system_bin_paths:
        pg_restore_paths += system_bin_paths
    if project_bin_path:
        pg_restore_paths.append(project_bin_path)
    pg_restore_path: str = pg_restore_paths[attempt-1] if pg_restore_paths \
        else ''
    max_attempts: int = len(pg_restore_paths)

    try:
        cmd_base: str = '{pg_restore_path} --exit-on-error --create {drop}' \
            '--dbname={database} --host={hostname} --port={port} ' \
            '--username={username} {path}'

        cmd_str: str = cmd_base.format(
            **root_connection_info,
            path=path,
            pg_restore_path=pg_restore_path,
            drop='--clean ' if dropdb else '')
        cmd: List[str] = cmd_str.split(' ')

        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True)

        if not silent:
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
    except FileNotFoundError as err:
        if attempt < max_attempts:
            restore_using_pgrestore(
                path=path, dropdb=dropdb, silent=silent, attempt=attempt+1)
        else:
            raise err


# TODO 2019.04.08-jef: Remove because requires superuser; can't do on Heroku.
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


# TODO 2019.04.08-jef: Remove because requires superuser; can't do on Heroku.
# def view_db_connections() -> List[dict]:
#     """View active connections to a db
#
#     Returns:
#         list(dict): List of active connections in the form of dictionaries
#         containing information about connections
#     """
#     # noinspection PyProtectedMember
#     from sqlalchemy.engine import ResultProxy
#
#     try:
#         db_name: str = current_app.config.get('DB_NAME', 'pmaapi')
#     except RuntimeError as err:
#         if 'Working outside of application context' not in str(err):
#             raise err
#         db_name: str = 'pmaapi'
#     statement = "SELECT * FROM pg_stat_activity WHERE datname = '%s'" \
#                 % db_name
#     conn: Connection = superuser_dbms_connection()
#
#     conn.execute("COMMIT")
#     result: ResultProxy = conn.execute(statement)
#     conn.close()
#
#     active_connections: List[dict] = []
#     for row in result:
#         conn_info = {}
#         for key_val in row.items():
#             conn_info = {**conn_info, **{key_val[0]: key_val[1]}}
#         active_connections.append(conn_info)
#
#     return active_connections


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


@aws_s3
def download_file_from_s3(
        filename: str, file_dir: str, dl_dir: str = TEMP_DIR) -> str:
    """Download a file from AWS S3

    Args:
        filename (str): Name of file to restore
        file_dir (str): Path to dir where file is stored
        dl_dir (str): Path to directory to download file

    Returns:
        str: Path to downloaded file
    """
    from botocore.exceptions import ClientError

    # create temp dir if doesn't exist
    if not os.path.exists(TEMP_DIR):
        os.mkdir(TEMP_DIR)

    s3 = boto3.resource('s3')
    download_from_path: str = os.path.join(file_dir, filename)
    download_to_path: str = os.path.join(dl_dir, filename)

    try:
        s3.Bucket(BUCKET).download_file(download_from_path, download_to_path)
    except ClientError as err:
        msg = 'The file requested was not found on AWS S3.\n' \
            if err.response['Error']['Code'] == '404' \
            else 'An error occurred while trying to download from AWS S3.\n'
        msg += '- File requested: ' + download_from_path
        raise PmaApiDbInteractionError(msg)

    return download_to_path


def dataset_version_to_name(version_number: int) -> str:
    """From dataset version number, get dataset name

    Args:
        version_number (int): Version number of dataset file

    Raises:
        FileNotFoundError: If dataset version not found on S3.

    Returns:
        str: Dataset name
    """
    err = 'Dataset version {} not found.'.format(str(version_number))
    filename: str = ''
    datasets: List[Dict[str, str]] = list_cloud_datasets()
    for d in datasets:
        if int(d['version_number']) == version_number:
            filename: str = d['name']

    if not filename:
        raise FileNotFoundError(err)

    return filename


def download_dataset(version_number: int) -> str:
    """Download dataset file from AWS S3

    Args:
        version_number (int): Version number of dataset file to download

    Returns:
        str: Path to downloaded file
    """
    filename: str = dataset_version_to_name(version_number)

    downloaded_file_path: str = download_file_from_s3(
        filename=filename,
        file_dir=S3_DATASETS_DIR_PATH,
        dl_dir=TEMP_DIR)

    return downloaded_file_path


@aws_s3
def list_s3_objects(bucket_name: str = BUCKET) \
        -> []:
    """List objects on AWS S3

    Args:
        bucket_name (str): Name of bucket holding object storage

    Returns:
        list[boto3.resources.factory.s3.ObjectSummary]: List of S3 objects
    """
    s3 = boto3.resource('s3')
    objects = s3.Bucket(bucket_name).objects.all()
    # result: List[boto3.resources.factory.s3.ObjectSummary]
    result: List = [x for x in objects]

    return result


def _format_datetime(dt: datetime) -> str:
    """Format datetime: YYYY-MM-DD #:##am/pm GMT

    Args:
        dt: Datetime object

    Returns:
        str: formatted datetime
    """
    utc_tell = '+0000'

    the_datetime_base: str = dt.strftime('%b %d, %Y %I:%M%p')
    utc_timezone_offset: str = dt.strftime('%z')
    formatted: str = the_datetime_base if utc_timezone_offset != utc_tell \
        else the_datetime_base + ' GMT'

    return formatted


def list_filtered_s3_files(
        path: str, detailed: bool = True, include_e_tag: bool = True) \
        -> Union[List[str], List[Dict[str, str]]]:
    """Gets list of S3 files w/ directories and path prefixes filtered out

    Args:
        path (str): Path to directory holding files
        detailed (bool): Print more than just object/file name? E.g. default
        metadata regarding upload date, custom metadata such as file version,
        etc.
        include_e_tag (bool): Include AWS S3 auto-generated unique e_tag
        identifiers? If true, any object dictionaries returned will include
        the first 6 characters of the e_tag under the key 'id'.

    Returns:
        list: Filenames
    """
    path2 = path + '/' if not path.endswith('/') else path
    path3 = path2[1:] if path2.startswith('/') else path2

    # objects: List[boto3.resources.factory.s3.ObjectSummary]
    objects: List = list_s3_objects(silent=True)
    # filtered: List[boto3.resources.factory.s3.ObjectSummary]
    filtered: List = [x for x in objects
                      if x.key.startswith(path3)
                      and x.key != path3]

    if not detailed:
        names_only: List[str] = [x.key for x in filtered]
        formatted: List[str] = [os.path.basename(x) for x in names_only]
        formatted.sort()
    else:
        formatted: List[Dict[str, str]] = []
        basic_metadata: List[Dict[str, str]] = []
        basic_metadata2: List[Dict[str, str]] = []

        # Sort
        # sorted: List[boto3.resources.factory.s3.ObjectSummary]
        sorted_list: List = \
            sorted(filtered, key=lambda x: x.last_modified, reverse=True)

        # Get basic metadata ascertainable from filename
        for x in sorted_list:
            obj_dict: Dict[str, str] = {
                'key':  x.key,
                'name': os.path.basename(x.key),
                'owner': x.owner['DisplayName'],
                'last_modified': _format_datetime(x.last_modified)}
            if include_e_tag:
                obj_dict['id']: str = \
                    x.e_tag.replace('"', '').replace("'", "")[0:6]
            basic_metadata.append(obj_dict)

        # Get metadata explicitly stored in S3 object
        for x in basic_metadata:
            # client: botocore.client.S3
            client = boto3.client('s3')
            obj_metadata_request: Dict = \
                client.head_object(Bucket=BUCKET, Key=x['key'])
            obj_metadata: Dict[str, str] = obj_metadata_request['Metadata']
            x2 = {**copy(x), **obj_metadata}
            basic_metadata2.append(x2)

        # Remove no-longer necessary 'key' key
        for x2 in basic_metadata2:
            x3 = copy(x2)
            x3.pop('key')  # no longer need key used to lookup obj in s3
            formatted.append(x3)

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


def list_cloud_datasets(detailed: bool = True) \
        -> Union[List[str], List[Dict[str, str]]]:
    """List pma api dataset spec files on AWS S3

    Args:
        detailed (bool): 'detailed' param to pass down to
        list_filtered_s3_files function.

    Returns:
        list: List of file names if not detailed, else list of objects
        containing file names and metadata.
    """
    # files: List[str] if not detailed else List[Dict[str, str]]
    files: List = list_filtered_s3_files(
        path=S3_DATASETS_DIR_PATH,
        detailed=detailed)

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
    # TODO: Remove this line after Dataset model removed
    # from_db: [str] = [x.dataset_display_name for x in Dataset.query.all()]
    from_db: [str] = []
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


def list_datasets(detailed: bool = True) \
        -> Dict[str, List[Union[str, Dict[str, str]]]]:
    """List available api data spec files

    Args:
        detailed (bool): 'detailed' param to pass down to list_cloud_datasets()

    Returns:
        dict: available backups, of form...
        {'local': [...], 'cloud': [...]
    """
    return {
        'local': list_local_datasets(),
        'cloud': list_cloud_datasets(detailed=detailed)
    }


def seed_users():
    """Creates users for fresh instance; currently just a superuser"""
    create_superuser()


def create_superuser(
        name: str = os.getenv('SUPERUSER_NAME', 'admin'),
        pw: str = os.getenv('SUPERUSER_PW')):
    """Create default super user

    The current iteration of PMA API only allows for one user, the super user.
    During DB initialization, this function is run. If there are no existing,
    users it will create the super user, else does nothing.

    Side effects:
        - Creates a new user in db with max privileges

    Args:
        name (str): Username
        pw (str): Plain text for password
    """
    users: List[User] = User.query.all()

    if not users:
        user_manager: UserManager = current_app.user_manager

        # TODO: Am I getting an error here just because of UserMixin / no
        #  __init__ present in child class?
        # noinspection PyArgumentList
        user = User(
            active=True,
            username=name,
            password=user_manager.hash_password(pw),
            first_name='PMA API',
            last_name='Admin')
        db.session.add(user)
        db.session.commit()


def restore_db_cloud(filename: str, silent: bool = False):
    """Restore database

    Args:
        filename (str): Name of file to restore
        silent (bool): Don't print updates?

    Side effects:
        Reverts database to state of backup file
    """
    if os.getenv('ENV_NAME') == 'development':
        path: str = download_file_from_s3(
            filename=filename,
            file_dir=S3_BACKUPS_DIR_PATH,
            dl_dir=BACKUPS_DIR)
        restore_db_local(path=path, silent=silent)
    else:
        # TODO: make same as test file
        dl_path: str = os.path.join(BACKUPS_DIR, filename)
        dl_url_base = 'https://{bucket}.s3.amazonaws.com/{key}'
        dl_url = dl_url_base.format(bucket=BUCKET, key=dl_path)
        restore_using_heroku_postgres(s3_url=dl_url, silent=silent)


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


def restore_db_local(path: str, silent: bool = False):
    """Restore database

    Args:
        path (str): Path to backup file
        silent (bool): Don't print updates?

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
        restore_using_pgrestore(path=path, dropdb=True, silent=silent)
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
def delete_s3_file(file_path: str):
    """Delete a file from AWS S3

    Args:
        file_path (str): Path to file on S3

    Side effects:
        - deletes file
    """
    import boto3

    s3 = boto3.resource('s3')
    s3.Object(BUCKET, file_path).delete()


def delete_backup(filename: str):
    """Delete backup file from storage

    Args:
        filename (str): Name of file

    Side effects:
        - deletes file
    """
    file_path: str = os.path.join(S3_BACKUPS_DIR_PATH, filename)

    delete_s3_file(file_path)


def delete_dataset(version_number: int):
    """Delete dataset from storage

    Args:
        version_number (int): Version of dataset to delete

    Side effects:
        - deletes file
    """
    filename: str = dataset_version_to_name(version_number)
    file_path: str = os.path.join(S3_DATASETS_DIR_PATH, filename)

    delete_s3_file(file_path)

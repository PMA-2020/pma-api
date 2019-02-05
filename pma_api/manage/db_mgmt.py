"""Database management"""
import csv
from copy import copy
from datetime import datetime
import glob
import logging
import ntpath
import os
import subprocess

import xlrd
from flask import Flask, current_app
from sqlalchemy.exc import DatabaseError, OperationalError

from pma_api import create_app, db
from pma_api.config import DATA_DIR, BACKUPS_DIR, Config, \
    IGNORE_SHEET_PREFIX, DATA_SHEET_PREFIX, AWS_S3_STORAGE_BUCKETNAME, \
    S3_BACKUPS_DIR_PATH, S3_DATASETS_DIR_PATH, S3_UI_DATA_DIR_PATH, \
    UI_DATA_DIR, DATASETS_DIR
from pma_api.error import InvalidDataFileError, PmaApiDbInteractionError, \
    PmaApiException
from pma_api.models import (Cache, Characteristic, CharacteristicGroup,
                            Country, Data, EnglishString, Geography, Indicator,
                            ApiMetadata, Survey, Translation, Dataset)
from pma_api.utils import most_common
from pma_api.manage.utils import log_process_stderr

METADATA_MODEL_MAP = (
    ('geography', Geography),
    ('country', Country),
    ('survey', Survey),
    ('char_grp', CharacteristicGroup),
    ('char', Characteristic),
    ('indicator', Indicator),
    ('translation', Translation),
)
DATA_MODEL_MAP = (
    ('data', Data),
)
TRANSLATION_MODEL_MAP = (
    ('translation', Translation),
)
ORDERED_MODEL_MAP = METADATA_MODEL_MAP + DATA_MODEL_MAP
FILE_LIST_IGNORES = ('.DS_Store', )
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
    .format(os.getenv('DATABASE_NAME', 'pmaapi'))


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
        silent = kwargs and 'silent' in kwargs and kwargs['silent']
        if not silent:
            print('Executing: ' + func.__name__)
        wrapper_kwargs_removed = \
            {k: v for k, v in kwargs.items() if k != 'silent'}
        try:
            return func(*args, **wrapper_kwargs_removed)
        except ClientError as err:
            if 'Access Denied' in str(err) or 'AccessDenied' in str(err):
                raise PmaApiDbInteractionError(msg)
            else:
                raise err

    return wrap


def get_file_by_glob(pattern):
    """Get file by glob.

    Args:
        pattern (str): A glob pattern.

    Returns:
        str: Path/to/first_file_found
    """
    found = glob.glob(pattern)
    try:
        return found[0]
    except IndexError:
        return ''


def get_api_data():
    """Get API data."""
    return get_file_by_glob(os.path.join(DATA_DIR, 'api_data*.xlsx'))


def get_ui_data():
    """Get API data."""
    return get_file_by_glob(os.path.join(DATA_DIR, 'ui_data*.xlsx'))


def make_shell_context():
    """Make shell context, for the ability to manipulate these models/tables
    from the command line shell.

    Returns:
        dict: Context for application manager shell.
    """
    return dict(app=create_app(os.getenv('FLASK_CONFIG', 'default')), db=db,
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


def init_data(wb):
    """Put all the data from the workbook into the database."""
    survey = {}
    indicator = {}
    characteristic = {}
    for record in Survey.query.all():
        survey[record.code] = record.id
    for record in Indicator.query.all():
        indicator[record.code] = record.id
    for record in Characteristic.query.all():
        characteristic[record.code] = record.id
    for ws in wb.sheets():
        if ws.name.startswith('data'):
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
                    Exception) as err:
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


def init_from_workbook(wb, queue):
    """Init from workbook.

    Args:
        wb (str): path to workbook file
        queue (tuple): Order in which to load models.
    """
    with xlrd.open_workbook(wb) as book:
        book = format_book(book)
        for sheetname, model in queue:
            if sheetname == 'data':  # actually done last
                init_data(book)
            else:
                ws = book.sheet_by_name(sheetname)
                init_from_sheet(ws, model)
    create_wb_metadata(wb)


def create_wb_metadata(wb_path):
    """Create metadata for Excel Workbook files imported into the DB.

    Args:
        wb_path (str) Path to Excel Workbook.
    """
    record = ApiMetadata(wb_path)
    db.session.add(record)
    db.session.commit()


def initdb_from_wb(_app: Flask = current_app,
                   api_file_path: str = get_api_data(),
                   ui_file_path: str = get_ui_data(),
                   overwrite: bool = False) -> dict:
    """Create the database.

    Args:
        _app (Flask): Flask application for context
        overwrite (bool): Overwrite database if True, else update.
        api_file_path (str): path to "API data file" spec xls file
        ui_file_path (str): path to "UIdata file" spec xls file

    Returns:
        dict: Results
    """
    backup_db()
    warnings = {}
    status = {
        'success': False,
        'warnings': warnings,
    }
    with _app.app_context():
        try:
            # Delete all tables except for 'datasets'
            if overwrite:
                db.metadata.drop_all(db.engine, tables=[x.__table__ for x in [
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
                    ApiMetadata]])

            # Create tables
            db.create_all()

            dataset_name = os.path.basename(api_file_path)
            dataset = Dataset.query.filter_by(
                dataset_display_name=dataset_name).first()
            if not dataset:
                db.session.add(Dataset(file_path=api_file_path,
                                       is_processing=True))
            db.session.commit()

            # Seed database
            if overwrite:
                # TODO: init_from_datasets_table if exists instead?
                init_from_workbook(wb=api_file_path, queue=ORDERED_MODEL_MAP)
                init_from_workbook(wb=ui_file_path,
                                   queue=TRANSLATION_MODEL_MAP)
                try:
                    Cache.cache_datalab_init(_app)
                except RuntimeError as err:
                    warnings['caching'] = caching_error.format(err)

            # TODO: moving up & changing; verify works and remove this comment
            # If DB is brand new, seed 'datasets' table too
            # database_is_brand_new = list(Dataset.query.all()) == []
            # if database_is_brand_new:
            #     new_dataset = Dataset(file_path=api_file_path)
            #     db.session.add(new_dataset)
            #     db.session.commit()

            dataset.register_active()

            try:
                backup_db()
            except Exception as err:
                warnings['backup'] = str(err)

        # Print error if DB background process is not loaded
        except OperationalError as err:
            msg = connection_error.format(str(err))
            raise PmaApiDbInteractionError(msg)
        except AttributeError as err:
            if "'NoneType' object has no attribute 'drivername'" in str(err):
                msg = (
                    'An error occurred while interacting with the database. '
                    'This can often happen when db related environmental '
                    'variables (e.g. DATABASE_URL) are not set or cannot be '
                    'accessed. Please check that they are set and being '
                    'loaded correctly.\n\n'
                    '- Original error:\n'
                    + type(err).__name__ + ': ' + str(err))
            else:
                msg = err
            raise PmaApiDbInteractionError(msg)

        backup_db()

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


def new_backup_path(ext: str = 'dump'):
    """Backup default path

    Args:
        ext (str): File extension to use

    Returns:
        str: Default path of backup file at specific date and time
    """
    import platform

    filename_base = 'pma-api-backup'
    datetime_str = str(datetime.now()).replace('/', '-').replace(':', '-')\
        .replace(' ', '_')
    op_sys = 'MacOS' if platform.system() == 'Darwin' else platform.system()
    filename = '_'.join([filename_base, op_sys, datetime_str]) + '.' + ext

    return os.path.join(BACKUPS_DIR, filename)


def backup_using_sql_file(path: str = new_backup_path(ext = 'sql')):
    """Backup using sql file

    Args:
        path (str): Path to save file

    Returns:
        str: path to backup file saved
    """
    import psycopg2
    import sys

    con = None
    table_names = []

    try:
        con = psycopg2.connect(database=Config.DATABASE_NAME,
                               user=Config.DATABASE_USER,
                               password=Config.DATABASE_PASSWORD,
                               port=Config.DATABASE_PORT)
        cur = con.cursor()
        cur.execute("""SELECT table_name FROM information_schema.tables
               WHERE table_schema = 'public'""")
        for table_tuple in cur.fetchall():
            table_names.append(table_tuple[0])

        f = open(path, 'w')
        for table in table_names:
            cur.execute('SELECT x FROM {}'.format(table))
            for row in cur:
                f.write('insert into {} values ({});'.format(table, str(row)))
        f.close()
    except psycopg2.DatabaseError as err:
        print('Error {}'.format(err))
        sys.exit(1)
    finally:
        if con:
            con.close()

    return path


def backup_using_pgdump_gz(path: str = new_backup_path(ext = 'gz')):
    """Backup using pg_dump

    Args:
        path (str): Path of file to save

    Raises
        PmaApiDbInteractionError: If did not succeed

    Returns:
        str: path to backup file saved
    """
    import gzip

    cmd = 'pg_dump -h localhost -U postgres {}'\
        .format(Config.DATABASE_NAME)\
        .split(' ')

    with gzip.open(path, 'wb') as f:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
        for line in iter(proc.stdout.readline, ''):
            f.write(line.encode('utf-8'))

    errors = proc.stderr.read()
    if errors:
        err_msg = ''
        for line in iter(proc.stderr.readline, ''):
            err_msg += line.encode('utf-8')
        if err_msg:
            raise PmaApiDbInteractionError(err_msg)

    proc.stderr.close()
    proc.stdout.close()
    proc.wait()

    return path


def backup_using_pgdump_dump(path: str = new_backup_path(ext = 'dump')):
    """Backup using pg_dump

    Args:
        path (str): Path of file to save

    Raises
        PmaApiDbInteractionError: If did not succeed

    Returns:
        str: path to backup file saved
    """
    cmd = 'pg_dump -Fc {} --file {}'\
        .format(Config.DATABASE_NAME, path)\
        .split(' ')

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)
    for line in iter(proc.stdout.readline, ''):
        print(line.encode('utf-8'))

    errors = proc.stderr.read()
    if errors:
        # err_msg = ''
        # for line in iter(proc.stderr.readline, ''):
        #     err_msg += line.encode('utf-8')
        # if err_msg:
        #     raise PmaApiDbInteractionError(err_msg)
        raise PmaApiDbInteractionError(errors)

    proc.stderr.close()
    proc.stdout.close()
    proc.wait()

    return path


def backup_local(path: str = '', method: str = 'dump'):
    """Backup database locally

    Args:
        path (str): Path to save file
        method (str): Method to back up file, e.g. 'gz', 'dump', etc

    Returns:
        str: Path to backup file saved

    Side effects:
        - Saves file at path
    """
    local_backup_method_map = {
        'gz': backup_using_pgdump_gz,
        'dump': backup_using_pgdump_dump,
        'sql': backup_using_sql_file
    }
    local_backup_func = local_backup_method_map[method]
    target_dir = os.path.dirname(path) if path else BACKUPS_DIR

    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    try:
        if path:
            saved_path = local_backup_func(path)
        else:
            saved_path = local_backup_func()
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
        s3.Bucket(AWS_S3_STORAGE_BUCKETNAME).put_object(Key=filepath, Body=f)
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


def backup_db(path: str = '', method: str = 'dump'):
    """Backup database locally and to the cloud

    Args:
        path (str): Path to save file
        method (str): Method to back up file, e.g. 'gz', 'dump', etc

    Side effects:
        - backup_local()
        - backup_cloud()
    """
    saved_path = backup_local(path, method)
    backup_db_cloud(saved_path)


def restore_using_pgrestore(path: str):
    """Backup using pg_restore

    Args:
        path (str): Path of file to restore
    """
    cmd = 'pg_restore -C -d postgres {}'\
        .format(path)\
        .split(' ')

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)
    for line in iter(proc.stdout.readline, ''):
        print(line.encode('utf-8'))

    errors = proc.stderr.read()
    if errors:
        log_process_stderr(proc.stderr, err_msg=db_mgmt_err)
        if 'could not open input file' in errors \
                or 'No such file or directory' in errors:
            raise FileNotFoundError(errors)
        else:
            raise PmaApiDbInteractionError(errors)

    proc.stderr.close()
    proc.stdout.close()
    proc.wait()


def drop_db(db_name: str = Config.DATABASE_NAME):
    """Drop database

    Args:
        db_name (str): Database name
    """
    cmd = 'dropdb {}'.format(db_name).split(' ')

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)
    for line in iter(proc.stdout.readline, ''):
        print(line.encode('utf-8'))
    errors = proc.stderr.read()
    if errors:
        db_exists = False if db_not_exist_tell in errors else True
        if db_exists:
            log_process_stderr(proc.stderr, err_msg=db_mgmt_err)
            raise PmaApiDbInteractionError(errors)

    proc.stderr.close()
    proc.stdout.close()
    proc.wait()


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
    download_path = os.path.join(directory, filename)

    try:
        s3.Bucket(AWS_S3_STORAGE_BUCKETNAME)\
            .download_file(filename, download_path)
    except ClientError as err:
        msg = 'The file requested was not found on AWS S3.\n' \
            if err.response['Error']['Code'] == '404' \
            else 'An error occurred while trying to download from AWS S3.\n'
        msg += '- File requested: ' + filename
        raise PmaApiDbInteractionError(msg)

    return download_path


@aws_s3
def list_s3_objects(bucket_name: str = AWS_S3_STORAGE_BUCKETNAME) -> []:
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
    from_file_system: [str] = list_local_files(path=path, name_contains='api_data')
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
    path = download_file_from_s3(filename=filename,
                                 directory=BACKUPS_DIR)
    restore_db_local(path)


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

    drop_db()

    try:
        restore_using_pgrestore(path)
    except Exception as err:
        if os.path.exists(emergency_backup):
            restore_using_pgrestore(emergency_backup)
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
    s3.Object(AWS_S3_STORAGE_BUCKETNAME, filename).delete()

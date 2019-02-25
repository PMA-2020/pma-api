"""Application manager."""
import os
from pathlib import Path
import sys
from sys import stderr

# noinspection PyPackageRequirements
from dotenv import load_dotenv
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand, upgrade as \
    flask_migrate_upgrade
from psycopg2 import DatabaseError
from sqlalchemy.exc import StatementError, ProgrammingError, OperationalError

from pma_api import create_app, db
from pma_api.config import PROJECT_ROOT_DIR
from pma_api.error import PmaApiDbInteractionError
from pma_api.manage.server_mgmt import store_pid
from pma_api.manage.db_mgmt import initdb_from_wb, init_from_workbook, \
    get_api_data, get_ui_data, TRANSLATION_MODEL_MAP, make_shell_context, \
    connection_error, write_data_file_to_db as write_data, backup_db, \
    restore_db, list_backups as listbackups, list_ui_data as listuidata, \
    list_datasets as listdatasets, backup_source_files as backupsourcefiles, \
    create_db, TaskTracker
from pma_api.models import Cache, ApiMetadata, Translation
from pma_api.utils import dict_to_pretty_json

load_dotenv(dotenv_path=Path(PROJECT_ROOT_DIR) / '.env')
app = create_app(os.getenv('FLASK_CONFIG', 'default'))
manager = Manager(app)
migrate = Migrate(app, db)


# TODO: backup db and restore
@manager.option('--overwrite', help='Drop tables first?', action='store_true')
def initdb(overwrite: bool = False, api_file_path: str = '',
           ui_file_path: str = ''):
    """Create the database.

    Args:
        overwrite (bool): Overwrite database if True, else update.
        api_file_path (str): Path to API spec file; if not present, gets
        from default path
        ui_file_path (str): Path to UI spec file; if not present, gets
        from default path
    """
    api_file = api_file_path if api_file_path else get_api_data()
    ui_file = ui_file_path if ui_file_path else get_ui_data()

    try:
        results = initdb_from_wb(overwrite=overwrite,
                                 api_file_path=api_file,
                                 ui_file_path=ui_file,
                                 _app=app)
    except PmaApiDbInteractionError as e:
        raise e
    except Exception as e:
        # to-do - restore db
        raise PmaApiDbInteractionError(e)

    warning_str = ''
    if results['warnings']:
        warning_str += '\nWarnings:'
        for k, v in results['warnings']:
            warning_str += '\n{}: {}'.format(k, v)
    result = 'Successfully initialized dataset.' if results['success'] \
        else 'Failed to initialize dataset.'

    print('\n', result, '\n', warning_str)


@manager.command
def translations():
    """Import all translations into the database."""
    with app.app_context():
        try:
            # TODO (jkp 2017-09-28) make this ONE transaction instead of many.
            db.session.query(ApiMetadata).delete()
            db.session.query(Translation).delete()
            db.session.commit()
            init_from_workbook(wb=get_api_data(), queue=TRANSLATION_MODEL_MAP)
            init_from_workbook(wb=get_ui_data(), queue=TRANSLATION_MODEL_MAP)
            cache_responses()
        except (StatementError, DatabaseError) as e:
            print(connection_error.format(str(e)), file=stderr)
        except RuntimeError as e:
            print('Error trying to execute caching. Is the server running?\n\n'
                  + '- Original error:\n'
                  + type(e).__name__ + ': ' + str(e))


@manager.command
def cache_responses():
    """Cache responses in the 'cache' table of DB."""
    with app.app_context():
        try:
            Cache.cache_datalab_init(app)
        except (StatementError, DatabaseError) as e:
            print(connection_error.format(str(e)), file=stderr)


@manager.command
def write_data_file_to_db(**kwargs):
    """Write data to db"""
    write_data(**kwargs)


@manager.option('--path', help='Custom path for backup file')
def backup(path: str = ''):
    """Backup db

    Args:
        path (str): Path to save backup file
    """
    if path:
        backup_db(path)
    else:
        backup_db()


@manager.option('--path', help='Path of backup file to restore, or the '
                               'filename to fetch from AWS S3')
def restore(path: str):
    """Restore db

    Args:
        path (str): Path to backup file
    """
    import inspect

    if not path:
        syntax = ' '.join([__file__,
                           inspect.currentframe().f_code.co_name,
                           '--path=PATH/TO/BACKUP'])
        print('\nMust specify path: ' + syntax, file=stderr)
        print('\nHere is a list of backups to choose from: \n',
              dict_to_pretty_json(listbackups()))
    else:
        restore_db(path)


@manager.command
def list_backups():
    """List available backups"""
    pretty_json = dict_to_pretty_json(listbackups())
    print(pretty_json)


@manager.command
def list_ui_data():
    """List available ui data"""
    pretty_json = dict_to_pretty_json(listuidata())
    print(pretty_json)


@manager.command
def list_datasets():
    """List available datasets"""
    pretty_json = dict_to_pretty_json(listdatasets())
    print(pretty_json)


@manager.command
def list_source_files():
    """List available source files: ui data and datasets"""
    print('Datasets: ')
    list_datasets()
    print('UI data files: ')
    list_ui_data()


@manager.command
def backup_source_files():
    """Backup available source files: ui data and datasets"""
    backupsourcefiles()


# TODO: Get this to work
def stderr_stdout_captured(func):
    """Capture stderr and stdout

    Args:
        func: A function

    Returns:
        str, str, any: stderr output, stdout output, return of function
    """
    import sys
    from io import StringIO

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured_stderr = sys.stderr = StringIO()
    captured_stdout = sys.stdout = StringIO()

    returned_value = func()

    _err: str = captured_stderr.getvalue()
    _out: str = captured_stdout.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    return _err, _out, returned_value


@manager.option('--attempt', help='Attempt number')
@manager.option('--silent', help='Print progress updates?')
def upgrade(attempt=None, silent=False):
    """Apply database migrations to database

    Args:
        attempt (int): Number of attempt
    """
    progress = TaskTracker(name='Database schema migration', queue=[
        'Beginning schema migration'
    ])
    max_attempts = 3
    this_attempt = attempt if attempt else 1

    if this_attempt == 1 and not silent:
        progress.begin()

    try:
        db.create_all()
        stderr_stdout_captured(
            flask_migrate_upgrade())
        progress.complete()
    except (ProgrammingError, OperationalError) as exc:
        if 'already exists' in str(exc):
            if not silent:
                print('Database schema already up-to-date. No migration '
                      'necessary.')
        elif 'does not exist' in str(exc) and this_attempt < max_attempts:
            # indicates missing tables, indicating full schema not yet created
            create_db()
            upgrade(attempt=this_attempt + 1)
        else:
            raise exc


@manager.command
def release():
    """Perform steps necessary for a deployment"""
    progress = TaskTracker(name='Deployment release process', queue=[
        'Beginning schema migration',
        'Initializing database'
    ])
    progress.begin()

    progress.next()
    upgrade(silent=True)

    progress.next()
    initdb(overwrite=True)


manager.add_command('shell', Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)  # e.g. 'upgrade', 'migrate'


if __name__ == '__main__':
    args = ' '.join(sys.argv)
    if 'runserver' in args:
        store_pid()
    try:
        manager.run()
    except PmaApiDbInteractionError as err:
        print(type(err).__name__ + ': ' + str(err), file=stderr)

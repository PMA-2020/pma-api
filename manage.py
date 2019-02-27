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
app = create_app(os.getenv('ENV_NAME', 'default'))
manager = Manager(app)
migrate = Migrate(app, db)


@manager.option('--overwrite', action='store_true', help='Drop tables first?')
@manager.option(
    '--force', action='store_true',
    help='Overwrite DB even if source data files present / '
         'supplied are same versions as those active in DB?')
def initdb(overwrite: bool = False, force: bool = False,
           api_file_path: str = get_api_data(),
           ui_file_path: str = get_ui_data()):
    """Create the database.

    Side effects:
        - Prints results

    Args:
        overwrite (bool): Overwrite database if True, else update.
        force (bool): Overwrite DB even if source data files present /
        supplied are same versions as those active in DB?'
        api_file_path (str): Path to API spec file; if not present, gets
        from default path
        ui_file_path (str): Path to UI spec file; if not present, gets
        from default path
    """
    results: dict = initdb_from_wb(
        overwrite=overwrite,
        force=force,
        api_file_path=api_file_path,
        ui_file_path=ui_file_path,
        _app=app)

    warning_str = ''
    if results['warnings']:
        warning_str += '\nWarnings:'
        warnings: dict = results['warnings']
        for k, v in warnings.items():
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


# TODO: Get this to work. then move to utils
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


# TODO: Address: ERROR [alembic.env] (psycopg2.ProgrammingError) column
#  "is_active" of relation "dataset" already exists
#  Maybe check alembic version in database?
@manager.option('--silent', action='store_true',
                help='Print progress updates?')
def upgrade(_attempt: int = None, silent: bool = False):
    """Apply database migrations to database

    Args:
        _attempt (int): Number of attempt iteration. Used only by function
        during recursive attempts.
        silent (bool): Print progress updates?
    """
    progress = TaskTracker(name='Database schema migration', queue=[
        'Beginning schema migration'
    ])
    already_complete = 'Database schema already up-to-date. No migration ' \
                       'necessary.'
    max_attempts = 3
    this_attempt = _attempt if _attempt else 1

    if this_attempt == 1 and not silent:
        progress.next()

    try:
        db.create_all()
        stderr_stdout_captured(
            flask_migrate_upgrade())
        if not silent:
            progress.complete()
    except (ProgrammingError, OperationalError) as exc:
        if 'already exists' in str(exc):
            if not silent:
                print(already_complete)
        elif 'does not exist' in str(exc) and this_attempt < max_attempts:
            # indicates missing tables, indicating full schema not yet created
            create_db()
            upgrade(_attempt=this_attempt + 1)
        else:
            raise exc


@manager.option(
    '--force', action='store_true',
    help='Use "--force" option when running "initdb" sub-command?')
@manager.option(
    '--overwrite', action='store_true',
    help='Use "--overwrite" option when running "initdb" sub-command?')
@manager.option(
    '--silent_upgrade', action='store_true',
    help='Use "--silent" option when running "upgrade" sub-command?')
def release(overwrite: bool = True, force: bool = False,
            silent_upgrade: bool = True):
    """Perform steps necessary for a deployment

    Args:
        force (bool): Use "--force" option when running "initdb" sub-command?
        overwrite (bool): Use "--overwrite" option when running "initdb"
        sub-command?
        silent_upgrade (bool): Use "--silent" option when running "upgrade"
        sub-command?
    """
    progress = TaskTracker(name='Deployment release process', queue=[
        'Beginning schema migration',
        'Initialize database'
    ])
    progress.next()
    upgrade(silent=silent_upgrade)

    progress.next()
    initdb(overwrite=overwrite, force=force)

    progress.complete()


manager.add_command('shell', Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)  # e.g. 'upgrade', 'migrate'


if __name__ == '__main__':
    args = ' '.join(sys.argv)
    if 'runserver' in args:  # native Manager command
        store_pid()
    manager.run()

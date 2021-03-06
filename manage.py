"""Application management CLI"""
import os
from pathlib import Path
import sys
from sys import stderr

# noinspection PyPackageRequirements
from dotenv import load_dotenv
from typing import Dict
from flask_script import Manager, Shell
from psycopg2 import DatabaseError
from sqlalchemy.exc import StatementError

from pma_api import create_app
from pma_api.config import PROJECT_ROOT_PATH
from pma_api.manage.server_mgmt import store_pid
from pma_api.manage.db_mgmt import get_api_data, get_ui_data, \
     make_shell_context, connection_error, backup_db, \
     restore_db, list_backups as listbackups, \
     list_ui_data as listuidata, list_datasets as listdatasets, \
     backup_source_files as backupsourcefiles
from pma_api.manage.initdb_from_wb import InitDbFromWb
from pma_api.models import db, Cache, ApiMetadata, Translation
from pma_api.utils import dict_to_pretty_json

load_dotenv(dotenv_path=Path(PROJECT_ROOT_PATH) / '.env')
app = create_app(os.getenv('ENV_NAME', 'default'))
manager = Manager(app)


@manager.option('-a', '--api_file_path', help='Custom path for api file')
@manager.option('-u', '--ui_file_path', help='Custom path for ui file')
def initdb(api_file_path: str, ui_file_path: str):
    """Initialize a fresh database instance.

    WARNING: If DB already exists, will drop it.

    Side effects:
        - Drops database
        - Creates database
        - Prints results

    Args:
        api_file_path (str): Path to API spec file; if not present, gets
        from default path
        ui_file_path (str): Path to UI spec file; if not present, gets
        from default path
    """
    api_fp = api_file_path if api_file_path else get_api_data()
    ui_fp = ui_file_path if ui_file_path else get_ui_data()
    results: Dict = InitDbFromWb(
        _app=app,
        api_file_path=api_fp,
        ui_file_path=ui_fp)\
        .run()

    warning_str = ''
    if results['warnings']:
        warning_str += '\nWarnings:'
        warnings: dict = results['warnings']
        for k, v in warnings.items():
            warning_str += '\n{}: {}'.format(k, v)
    result = 'Successfully initialized dataset.' if results['success'] \
        else 'Failed to initialize dataset.'

    print('\n' + result + '\n' + warning_str)


@manager.command
def translations():
    """Import all translations into the database."""
    with app.app_context():
        try:
            # TODO 2017.09.28-jkp make one transaction instead of many
            db.session.query(ApiMetadata).delete()
            db.session.query(Translation).delete()
            db.session.commit()
            db_initializer = InitDbFromWb()
            db_initializer.init_api_worksheet('translation')
            db_initializer.init_client_ui_data()
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


@manager.command
def release():
    """Perform steps necessary for a deployment"""
    print('Deployment release task: Beginning')
    initdb(api_file_path='', ui_file_path='')
    print('Deployment release task: Complete')


manager.add_command('shell', Shell(make_context=make_shell_context))


if __name__ == '__main__':
    args = ' '.join(sys.argv)
    if 'runserver' in args:  # native Manager command
        store_pid()
    manager.run()

"""Application configuration classes."""
import os
from pathlib import Path

# noinspection PyPackageRequirements
from dotenv import load_dotenv


PACKAGE_DIR_PATH: str = os.path.dirname(__file__)
PACKAGE_DIR_NAME: str = os.path.basename(PACKAGE_DIR_PATH)
PROJECT_ROOT_PATH = \
    os.path.abspath(os.path.join(PACKAGE_DIR_PATH, '..'))
load_dotenv(dotenv_path=Path(PROJECT_ROOT_PATH) / '.env')

TEMP_DIR: str = os.path.join(PROJECT_ROOT_PATH, 'temp')
DATA_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT_PATH, 'data'))
BINARY_DIR: str = \
    os.path.abspath(os.path.join(PACKAGE_DIR_PATH, 'bin'))
DATASETS_DIR: str = DATA_DIR
UI_DATA_DIR: str = DATA_DIR
BACKUPS_DIR: str = os.path.abspath(os.path.join(DATA_DIR, 'db_backups'))
LOGS_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT_PATH, 'logs'))
ERROR_LOG_PATH = os.path.join(LOGS_DIR, 'error-logfile.log')
# noinspection PyUnresolvedReferences
PID_FILE_PATH: str = os.path.join(PROJECT_ROOT_PATH, 'pma-api_process-id.pid')
API_DATASET_FILE_PREFIX = 'api_data'
UI_DATASET_FILE_PREFIX = 'ui_data'
FILE_LIST_IGNORES = ('.DS_Store', )

REFERENCES = {  # TODO: What this is used for should be implemented different
    'routes': {
        'datalab_init': 'v1/datalab/init'
    },
    'binaries': {
        'pg_dump': {
            'system': 'pg_dump',
            'project': os.path.join(
                BINARY_DIR, 'pg_dump', '9.6.0', 'MacOS', 'pg_dump')
        },
        'pg_restore': {
            'system': 'pg_restore',
            'project': os.path.join(
                BINARY_DIR, 'pg_restore', '9.5.4', 'MacOS', 'pg_restore')
        },
        'heroku': {
            'system': 'heroku',
            'project': os.path.join(
                BINARY_DIR, 'heroku', '7.22.2', 'MacOS', 'heroku')
        },
    }
}

UNIVERSAL_IGNORE_PREFIX = '__'
IGNORE_FIELD_PREFIX = UNIVERSAL_IGNORE_PREFIX
IGNORE_SHEET_PREFIX = UNIVERSAL_IGNORE_PREFIX
DATA_SHEET_PREFIX = 'data_'
ACCEPTED_DATASET_EXTENSIONS = ('csv', 'xls', 'xlsx')

PROJECT_NAME = 'pma-api'
ENV_NAME = os.getenv('ENV_NAME', 'development')
HEROKU_INSTANCE_APP_NAME: str = PROJECT_NAME if ENV_NAME == 'production' \
    else PROJECT_NAME + '-' + 'staging' if ENV_NAME == 'staging' else ''
AWS_S3_STORAGE_BUCKETNAME: str = os.getenv('BUCKET_NAME', 'pma-api-backups')
S3_BACKUPS_DIR_PATH = 'database/backups/'
S3_DATASETS_DIR_PATH = 'datasets/versions/'
S3_UI_DATA_DIR_PATH = 'ui/versions/'

SQLALCHEMY_MODEL_ATTR_QUERY_IGNORES = ('_sa_instance_state', )
LOCAL_DEVELOPMENT_URL: str = os.getenv(
    'LOCAL_DEVELOPMENT_URL', 'http://localhost:5000')
ASYNC_SECONDS_BETWEEN_STATUS_CHECKS = 5

# CELERY_QUEUE is also specified in makefile
CELERY_QUEUE = 'pma-api-{}'.format(ENV_NAME)


class Config:
    """Base configuration."""
    DEBUG = False
    TESTING = False
    CSRF_ENABLED = True
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', 5432)
    DB_USER = os.getenv('DB_USER', 'pmaapi')
    DB_PASS = os.getenv('DB_PASS', 'pmaapi')
    DB_NAME = os.getenv('DB_NAME', 'pmaapi')

    DB_ROOT_HOST = os.getenv('DB_ROOT_HOST', 'localhost')
    DB_ROOT_PORT = os.getenv('DB_ROOT_PORT', 5432)
    DB_ROOT_USER = os.getenv('DB_ROOT_USER', 'postgres')
    DB_ROOT_PASS = os.getenv('DB_ROOT_PASS', 'postgres')
    DB_ROOT_NAME = os.getenv('DB_ROOT_NAME', 'postgres')

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    CELERY_BROKER_URL = os.getenv('MESSAGE_BROKER_URL')
    CELERY_RESULT_BACKEND: str = CELERY_BROKER_URL
    STAGING_URL = os.getenv('STAGING_URL')
    PRODUCTION_URL = os.getenv('PRODUCTION_URL')
    LOCAL_DEVELOPMENT_URL: str = LOCAL_DEVELOPMENT_URL

    # Flask-User settings
    SECRET_KEY = os.getenv('SECRET_KEY')
    USER_APP_NAME = "PMA API"  # Shown in email templates and page footers
    USER_ENABLE_EMAIL = False  # Auth by email
    USER_ENABLE_USERNAME = True    # Auth by username
    USER_REQUIRE_RETYPE_PASSWORD = False


class StagingConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_ECHO = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'staging': StagingConfig,
    # And the default is...
    'default': DevelopmentConfig
}

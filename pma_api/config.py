"""Application configuration classes."""
import os
from pathlib import Path

# noinspection PyPackageRequirements
from dotenv import load_dotenv


PROJECT_ROOT_DIR = \
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(dotenv_path=Path(PROJECT_ROOT_DIR) / '.env')

DATA_DIR = os.path.abspath(os.path.join(PROJECT_ROOT_DIR, 'data'))
DATASETS_DIR = DATA_DIR
UI_DATA_DIR = DATA_DIR
BACKUPS_DIR = os.path.abspath(os.path.join(DATA_DIR, 'db_backups'))
LOGS_DIR = os.path.abspath(os.path.join(PROJECT_ROOT_DIR, 'logs'))
ERROR_LOG_PATH = os.path.join(LOGS_DIR, 'error-logfile.log')
PID_FILE_PATH = os.path.join(PROJECT_ROOT_DIR, 'pma-api_process-id.pid')

REFERENCES = {  # TODO: What this is used for should be implemented different
    'routes': {
        'datalab_init': 'v1/datalab/init'
    }
}

UNIVERSAL_IGNORE_PREFIX = '__'
IGNORE_FIELD_PREFIX = UNIVERSAL_IGNORE_PREFIX
IGNORE_SHEET_PREFIX = UNIVERSAL_IGNORE_PREFIX
DATA_SHEET_PREFIX = 'data_'
ACCEPTED_DATASET_EXTENSIONS = ('csv', 'xls', 'xlsx')

FLASK_CONFIG_ENV_KEY = 'FLASK_CONFIG'
AWS_S3_STORAGE_BUCKETNAME = os.getenv('BUCKET_NAME', 'pma-api-backups')
S3_BACKUPS_DIR_PATH = 'database/backups/'
S3_DATASETS_DIR_PATH = 'datasets/versions/'
S3_UI_DATA_DIR_PATH = 'ui/versions/'

SQLALCHEMY_MODEL_ATTR_QUERY_IGNORES = ('_sa_instance_state', )
LOCAL_DEVELOPMENT_URL = os.getenv('LOCAL_DEVELOPMENT_URL',
                                  'http://localhost:5000')
ASYNC_SECONDS_BETWEEN_STATUS_CHECKS = 5


def temp_folder_path() -> str:
    """Get the path to temp upload folder.

    Returns:
        str: path
    """
    from pma_api.utils import os_appropriate_folder_path
    return os_appropriate_folder_path('temp')


def data_folder_path() -> str:
    """Get the path to data folder.

    Returns:
        str: path
    """
    from pma_api.utils import os_appropriate_folder_path
    return os_appropriate_folder_path('data')


class Config:
    """Base configuration."""
    TESTING = False
    CSRF_ENABLED = True
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DATABASE_NAME = os.getenv('DATABASE_NAME', 'pmaapi')
    DATABASE_USER = os.getenv('DATABASE_USER', 'pmaapi')
    DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD', 'pmaapi')
    DATABASE_PORT = os.getenv('DATABASE_PORT', '5432')

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    CELERY_BROKER_URL = os.getenv('MESSAGE_BROKER_URL')
    CELERY_RESULT_BACKEND = CELERY_BROKER_URL
    STAGING_URL = os.getenv('STAGING_URL')
    PRODUCTION_URL = os.getenv('PRODUCTION_URL')
    LOCAL_DEVELOPMENT_URL = LOCAL_DEVELOPMENT_URL

    BROKER_TRANSPORT_OPTIONS = {
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.2,
    }


class StagingConfig(Config):
    """Production configuration."""
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Production configuration."""
    SQLALCHEMY_ECHO = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # SQLALCHEMY_ECHO = True
    SQLALCHEMY_ECHO = False  # TODO: temp


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'staging': StagingConfig,
    # And the default is...
    'default': DevelopmentConfig
}

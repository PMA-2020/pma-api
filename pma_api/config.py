"""Application configuration classes."""
import os
from pathlib import Path

# noinspection PyPackageRequirements
from dotenv import load_dotenv


PROJECT_ROOT_DIR = \
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(dotenv_path=Path(PROJECT_ROOT_DIR) / '.env')

DATA_DIR = os.path.abspath(os.path.join(PROJECT_ROOT_DIR, 'data'))
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

FLASK_CONFIG_ENV_KEY = 'FLASK_CONFIG'
AWS_S3_BACKUPS_BUCKETNAME = os.getenv('BUCKET_NAME', 'pma-api-backups')


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
    REDIS_URL = os.getenv('REDIS_URL')
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    STAGING_URL = os.getenv('STAGING_URL')
    PRODUCTION_URL = os.getenv('PRODUCTION_URL')
    LOCAL_DEVELOPMENT_URL = os.getenv('LOCAL_DEVELOPMENT_URL',
                                      'http://localhost:5000')


class StagingConfig(Config):
    """Production configuration."""
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Production configuration."""
    SQLALCHEMY_ECHO = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'staging': StagingConfig,
    # And the default is...
    'default': DevelopmentConfig
}

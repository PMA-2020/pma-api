"""Application configuration classes."""
import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""
    TESTING = False
    CSRF_ENABLED = True
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # try:
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    # except KeyError:
    #     SQLALCHEMY_DATABASE_URI = 'sqlite:///'+os.path.join(basedir, 'dev.db')


class StagingConfig(Config):
    """Production configuration."""
    pass


class ProductionConfig(Config):
    """Production configuration."""
    pass


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'dev.db')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'staging': StagingConfig,
    # And the default is...
    'default': DevelopmentConfig
}

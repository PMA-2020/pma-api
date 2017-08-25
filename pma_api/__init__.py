"""Definition of application object."""
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import config


db = SQLAlchemy()


def create_app(config_name):
    """Create configured Flask application.

    Args:
        config_name (str): Name of the configuration to be used.

    Returns:
        Flask: Configured Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)

    from .api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint)

    return app


app = Flask(__name__)
config_name = 'staging'
# config_name = os.environ('FLASK_APP', 'default')
# app.config.from_object(config(os.environ['FLASK_APP', 'default']))
app.config.from_object(config[config_name])

db.init_app(app)

from .api_1_0 import api as api_1_0_blueprint
app.register_blueprint(api_1_0_blueprint)


def run():
    """Run."""
    pass

# def gunicorn_run():
#     """Gunicorn run."""
#     config_name = os.environ('FLASK_APP', 'default')
#     app = create_app(config_name)
#     return app

if __name__ == '__main__':
    config_name = os.environ('FLASK_APP', 'default')
    app = create_app(config_name)
    run()

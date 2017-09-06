"""Definition of application object."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

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

    CORS(app)
    db.init_app(app)

    from .api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix='/v1')

    app.add_url_rule('/', view_func=lambda: 'To be implemented.')

    return app

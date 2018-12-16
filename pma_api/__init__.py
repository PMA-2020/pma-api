"""Definition of application object."""
import os

from celery import Celery
from flask_cors import CORS

from pma_api.config import FLASK_CONFIG_ENV_KEY
from pma_api.models import db


def create_app(config_name=os.getenv(FLASK_CONFIG_ENV_KEY, 'default')):
    """Create configured Flask application.

    Args:
        config_name (str): Name of the configuration to be used.

    Returns:
        Flask: Configured Flask application.
    """
    from pma_api.routes.root_routes import root
    from pma_api.app import PmaApiFlask
    from pma_api.config import config

    # noinspection PyShadowingNames
    app = PmaApiFlask(__name__)
    app.config.from_object(config[config_name])

    CORS(app)
    db.init_app(app)

    celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)

    app.register_blueprint(root)
    from pma_api.routes.endpoints.api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix='/v1')

    return app

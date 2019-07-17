"""Creation for application instance"""
import os

from flask_cors import CORS
from flask_user import UserManager

from pma_api.app import PmaApiFlask


def create_app(config_name: str = os.getenv('ENV_NAME', 'default')) \
        -> PmaApiFlask:
    """Create configured Flask application.

    Args:
        config_name (str): Name of the configuration to be used.

    Returns:
        PmaApiFlask: Configured Flask application.
    """
    from pma_api.config import config
    from pma_api.models import db, User
    from pma_api.routes import root

    _app = PmaApiFlask(__name__)
    _app.config.from_object(config[config_name])

    CORS(_app)

    db.init_app(_app)
    UserManager(_app, db, User)

    _app.register_blueprint(root)
    from pma_api.routes.endpoints.api_1_0 import api as api_1_0_blueprint
    _app.register_blueprint(api_1_0_blueprint, url_prefix='/v1')

    return _app

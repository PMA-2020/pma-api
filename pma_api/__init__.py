"""Definition of application object."""
# import logging
import os

from flask_cors import CORS
from flask_user import UserManager

from pma_api.models import db


def create_app(config_name=os.getenv('ENV_NAME', 'default')):
    """Create configured Flask application.

    Args:
        config_name (str): Name of the configuration to be used.

    Returns:
        Flask: Configured Flask application.
    """
    from pma_api.app import PmaApiFlask
    from pma_api.config import config
    from pma_api.models import User
    from pma_api.routes import root

    # noinspection PyShadowingNames
    app = PmaApiFlask(__name__)
    app.config.from_object(config[config_name])

    CORS(app)
    # logging.getLogger('flask_cors').level = logging.DEBUG  # TODO: Temp

    db.init_app(app)

    # TODO: Following quickstart; Not sure why assigned and not just declared
    #  - jef 2019/03/11
    # noinspection PyUnusedLocal
    user_manager = UserManager(app, db, User)


    app.register_blueprint(root)
    from pma_api.routes.endpoints.api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix='/v1')

    return app

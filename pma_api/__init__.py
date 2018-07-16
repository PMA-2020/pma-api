"""Definition of application object."""
from flask import Blueprint, jsonify
from flask_cors import CORS

from .app import PmaApiFlask
from .config import config
from .models import db
from .response import QuerySetApiResult


root = Blueprint('root', __name__)


@root.route('/version')
def show_version():
    """Show API version data."""
    return jsonify(QuerySetApiResult.metadata())


def create_app(config_name):
    """Create configured Flask application.

    Args:
        config_name (str): Name of the configuration to be used.

    Returns:
        Flask: Configured Flask application.
    """
    # noinspection PyShadowingNames
    app = PmaApiFlask(__name__)
    app.config.from_object(config[config_name])

    CORS(app)
    db.init_app(app)
    app.register_blueprint(root)

    from .api_1_0 import api as api_1_0_blueprint
    from .api_1_0.collection import get_resources
    app.register_blueprint(api_1_0_blueprint, url_prefix='/v1')

    # TODO: (jef/jkp 2017-08-29) Investigate mimetypes in accept headers.
    # See: flask.pocoo.org/snippets/45/ Needs: Nothing?
    request_headers = 'application/json'  # default for now
    if request_headers == 'text/html':
        # Also can re-route to /docs
        app.add_url_rule('/', view_func=lambda: 'Documentation')
    else:
        app.add_url_rule('/', view_func=lambda: get_resources())

    return app

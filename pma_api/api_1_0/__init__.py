"""API Routes."""
from flask import Blueprint, jsonify

from ..queries import DatalabData

api = Blueprint('api', __name__)
__version__ = '1.0'

# pylint: disable=wrong-import-position
from . import collection, datalab


@api.route('/')
def root():
    """Root route.

    Returns:
        func: get_resources() if 'application/json'
        func: get_docs() if 'text/html'
    """
    # TODO: (jef/jkp 2017-08-29) Investigate mimetypes in accept headers.
    # See: flask.pocoo.org/snippets/45/ Needs: Nothing?
    request_headers = 'application/json'  # default for now
    if request_headers == 'text/html':
        return 'Documentation.'
    return collection.get_resources()


@api.route('/version')
def show_version():
    """Show API version."""
    response = {
        'version': __version__
    }
    return jsonify(response)

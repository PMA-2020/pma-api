"""API Routes."""
from flask import Blueprint

from pma_api import root_route

api = Blueprint('api', __name__)

# pylint: disable=wrong-import-position
from . import collection, datalab


@api.route('/')
def root():
    """Root route.

    .. :quickref: Root; Redirects to resources list or documentation depending
     on MIME type.

    Returns:
        func: get_resources() if 'application/json'
        func: redirect to docs if 'text/html'
    """
    return root_route()

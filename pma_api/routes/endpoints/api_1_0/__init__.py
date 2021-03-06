"""API Routes."""
from flask import Blueprint

from pma_api.routes import root_route

api = Blueprint('api', __name__)

# pylint: disable=wrong-import-position
from pma_api.routes.endpoints.api_1_0 import collection, datalab, dynamic


@api.route('/')
def root():
    """Root route.

    .. :quickref: Root; Redirects to resources list or documentation depending
     on MIME type

    Args:
        n/a

    Returns:
        func: get_resources() if 'application/json'
        func: redirect() to docs if 'text/html'

    Details:
        Redirects implicitly if MIME type does not explicitly match what is
        expected.
    """
    return root_route()

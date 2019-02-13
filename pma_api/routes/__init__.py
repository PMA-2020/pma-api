"""Root routes"""
from flask import Blueprint, redirect, request


root = Blueprint('root', __name__)

# pylint: disable=wrong-import-position
from . import administration, version, docs


@root.route('/')
def root_route():
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
    request_headers = request.accept_mimetypes\
        .best_match(['application/json', 'text/html'])

    if request_headers == 'text/html':
        return redirect('http://api-docs.pma2020.org', code=302)
    else:
        from .endpoints.api_1_0.collection import get_resources as res
        return res() if request_headers == 'application/json' else res()

"""Routes related to the datalab."""
from flask import request, render_template

from . import api
from . import caching
from ..models import Cache
from ..response import ApiResult, QuerySetApiResult
from ..queries import DatalabData


@api.route('/admin')
def admin_route():
    """Admin route

    .. :quickref: admin; stuff 

    Args:


    Query Args:


    Returns:


    Details:


    Example:

    """

    """return QuerySetApiResult(json_obj, 'json', queryInput=query_input,
                             chartOptions=chart_options)"""
    return render_template('index.html')

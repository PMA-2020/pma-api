"""Routes related specifically to the admin portal."""
from flask import render_template

from . import api


@api.route('/admin')
def admin_route():
    """Route to admin portal for uploading and managing datasets.

    .. :quickref: admin; Route to admin portal for uploading and managing
    datasets.

    Args: n/a

    Query Args: n/a

    Returns:
        flask.render_template(): A rendered HTML template.

    Examples: n/a

    Details:
        For more information on the features that will be added to this route,
        take a look at: https://github.com/PMA-2020/pma-api/issues/32
    """

    # - Temporarily here just for reference -jef, 2018/09/04
    # return QuerySetApiResult(json_obj, 'json', queryInput=query_input,
    #                          chartOptions=chart_options)
    return render_template('index.html')

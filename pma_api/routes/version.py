"""Version related routes"""
from flask import jsonify

from pma_api.response import QuerySetApiResult
from pma_api.routes import root


@root.route('/version')
def show_version():
    """Show API version data.

    .. :quickref: Version; API versioning data.

    Args:
        n/a

    Returns:
        String: Version number.

    Details:
        Displays API's 2-part semantic version number. ALso displays versioning
        for datasets used.

    Example:
        .. code-block:: json
           :caption: GET /v1/version
           :name: example-of-endpoint-version

            {
              "datasetMetadata": [
                {
                  "createdOn": "Fri, 13 Jul 2018 20:25:42 GMT",
                  "hash": "339ce036bdee399d449f95a1d4b3bb8f",
                  "name": "api_data-2018.03.19-v29-SAS",
                  "type": "api"
                },
                {
                  "createdOn": "Fri, 13 Jul 2018 20:25:43 GMT",
                  "hash": "469542a93241da0af80269b6d7352600",
                  "name": "ui_data-2017.10.02-v4-jef",
                  "type": "ui"
                }
              ],
              "version": "0.1.9"
            }
    """
    return jsonify(QuerySetApiResult.metadata())

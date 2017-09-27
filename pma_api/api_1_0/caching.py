"""Caching."""
from flask import url_for

from .. import db
from ..models import Cache, SourceData


KEY_DATALAB_INIT = 'v1/datalab/init'


def cache_datalab_init(app):
    """Add /v1/datalab/init to the server cache.

    This method checks the cache. If there is nothing cached or if the md5s do
    not match, then a new cached response is generated and saved.

    Args:
        app (Flask): The Flask app. There must be a current app context.
    """
    source_data_md5 = SourceData.get_current_api_data().md5_checksum
    current_cache = Cache.get(KEY_DATALAB_INIT)
    if not current_cache or current_cache.source_data_md5 != source_data_md5:
        url = url_for('api.get_datalab_init')
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        with app.test_request_context(url, headers=headers):
            api_result = app.view_functions['api.get_datalab_init']()
            response = api_result.to_response()
            value = response.get_data(as_text=True).strip()
            mimetype = response.mimetype
            if current_cache:
                current_cache.value = value
                current_cache.mimetype = mimetype
                current_cache.source_data_md5 = source_data_md5
            else:
                new_cache = Cache(key=KEY_DATALAB_INIT, value=value,
                                  mimetype=mimetype,
                                  source_data_md5=source_data_md5)
                db.session.add(new_cache)
            db.session.commit()

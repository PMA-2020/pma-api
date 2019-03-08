"""Metadata table."""
import os
from hashlib import md5

from flask import url_for, Flask, current_app

from pma_api.config import REFERENCES
from . import db


class ApiMetadata(db.Model):
    """Metadata."""

    __tablename__ = 'api_metadata'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String)
    type = db.Column(db.String, index=True)
    md5_checksum = db.Column(db.String)
    blob = db.Column(db.LargeBinary)
    created_on = db.Column(db.DateTime, default=db.func.now(),
                           onupdate=db.func.now(), index=True)

    def __init__(self, path):
        """Metadata init."""
        filename = os.path.splitext(os.path.basename(path))[0]
        self.name = filename
        if filename.startswith('api'):
            self.type = 'api'
        elif filename.startswith('ui'):
            self.type = 'ui'
        self.blob = open(path, 'rb').read()
        self.md5_checksum = md5(self.blob).hexdigest()

    @classmethod
    def get_current_api_data(cls):
        """Return the record for the most recent API data."""
        record = cls.query.filter_by(type='api').first()
        return record

    def to_json(self):
        """Return dictionary ready to convert to JSON as response.

        Returns:
            dict: API response ready to be JSONified.
        """
        result = {
            'name': self.name,
            'hash': self.md5_checksum,
            'type': self.type,
            'createdOn': self.created_on
        }
        return result


class Cache(db.Model):
    """Cache for API responses."""

    __tablename__ = 'cache'
    key = db.Column(db.String, primary_key=True)
    value = db.Column(db.String, nullable=False)
    mimetype = db.Column(db.String)
    source_data_md5 = db.Column(db.String)

    # TODO: Should be generalized function for all routes
    @staticmethod
    def cache_route(route: str, app: Flask = current_app):
        """Add route to the server cache

        This method checks the cache. If there is nothing cached or if the md5s
        do not match, then a new cached response is generated and saved.

        Args:
            route (str): route to cache
            app (Flask): The Flask app. There must be a current app context.
        """
        source_data_md5 = ApiMetadata.get_current_api_data().md5_checksum
        # example route: 'datalab_init': 'v1/datalab/init'
        # TODO: use 'cache_datalab_init' as template
        print(route, source_data_md5, app)

    @staticmethod
    def cache_datalab_init(app: Flask = current_app):
        """Add /v1/datalab/init to the server cache.

        This method checks the cache. If there is nothing cached or if the md5s
        do not match, then a new cached response is generated and saved.

        Args:
            app (Flask): The Flask app. There must be a current app context.
        """
        source_data_md5 = ApiMetadata.get_current_api_data().md5_checksum
        current_cache = Cache.get(REFERENCES['routes']['datalab_init'])

        if not current_cache \
                or current_cache.source_data_md5 != source_data_md5:
            url = url_for('api.get_datalab_init')
            headers = {'X-Requested-With': 'XMLHttpRequest'}
            with app.test_request_context(url, headers=headers):
                api_result = \
                    app.view_functions['api.get_datalab_init'](cached=False)
                response = api_result.to_response()
                value = response.get_data(as_text=True).strip()
                mimetype = response.mimetype
                if current_cache:
                    current_cache.value = value
                    current_cache.mimetype = mimetype
                    current_cache.source_data_md5 = source_data_md5
                else:
                    new_cache = Cache(key=REFERENCES['routes']['datalab_init'],
                                      value=value,
                                      mimetype=mimetype,
                                      source_data_md5=source_data_md5)
                    db.session.add(new_cache)
                db.session.commit()

    @classmethod
    def get(cls, key):
        """Return a record by key."""
        return cls.query.filter_by(key=key).first()

    def __repr__(self):
        """Give a representation of this record."""
        return "<Cache key='{}'>".format(self.key)

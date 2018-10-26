"""Metadata table."""
import os
from hashlib import md5

from . import db


class SourceData(db.Model):
    """Metadata."""

    __tablename__ = 'metadata'
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

    @classmethod
    def get(cls, key):
        """Return a record by key."""
        return cls.query.filter_by(key=key).first()

    def __repr__(self):
        """Give a representation of this record."""
        return "<Cache key='{}'>".format(self.key)

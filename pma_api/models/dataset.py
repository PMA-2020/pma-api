from datetime import datetime
from hashlib import md5

from . import db


class Dataset(db.Model):
    """"""


'''
url: string / varchar ~256
datasetDisplayName: string / varchar ~256
uploadDate: dateTime?, string / varchar ~256?
versionNumber: string / varchar ~256, semvar? int?
datasetType: string / varchar; factor var of ('data', 'metadata', 'dataAndMetadata')
datasetSubType: string / varchar ~256?; domain of, ('CCRR', 'METADATA_CLASS', 'all'/'full')
isActiveStaging: boolean
isActiveProduction: boolean
'''

    __tablename__ = 'dataset'
    ID = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String)
    datasetDisplayName = db.Column(db.String)
    uploadDate = db.Column(db.String)
    versionNumber = db.Column(db.String)
    datasetType = db.Column(db.String)
    datasetSubType = db.Column(db.String)
    isActiveStaging = db.Column(db.Boolean)
    isActiveProduction = db.Column(db.Boolean)





    @classmethod
    def get(cls, ID):
        """Return a record by ID."""
        return cls.query.filter_by(ID=ID).first()

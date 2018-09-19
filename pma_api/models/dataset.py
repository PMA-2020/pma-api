from datetime import datetime
from hashlib import md5

from . import db


class Dataset(db.Model):
    """

    datasetType: string / varchar; factor var of ('data', 'metadata', 'full')
    datasetSubType: string / varchar ~256?; domain of, ('CCRR', 'METADATA_CLASS', 'all'/'full')

    Example usage:
           new_dataset = Dataset(file_path)

    """

    __tablename__ = 'dataset'
    ID = db.Column(db.Integer, primary_key=True)
    data = db.BLOB
    datasetDisplayName = db.Column(db.String, nullable=False)
    uploadDate = db.Column(db.String, nullable=False)
    versionNumber = db.Column(db.String, nullable=False, unique = True)
    datasetType = db.Column(db.String, nullable=False)
    datasetSubType = db.Column(db.String, nullable=False)
    isActiveStaging = db.Column(db.Boolean, nullable=False)
    isActiveProduction = db.Column(db.Boolean, nullable=False)

    def __init__(self, file_path):


        """Initialize instance of dataset



        """
        '''kwargs['is_favorite'] = bool(kwargs['is_favorite'])
        self.update_kwargs_english(kwargs, 'level1', 'level1_id')
        self.update_kwargs_english(kwargs, 'level2', 'level2_id')
        self.update_kwargs_english(kwargs, 'domain', 'domain_id')
        self.update_kwargs_english(kwargs, 'definition', 'definition_id')
        self.update_kwargs_english(kwargs, 'label', 'label_id')
        '''

        super(dataset, self).__init__()



    @classmethod
    def get(cls, ID):
        """Return a record by ID."""
        return cls.query.filter_by(ID=ID).first()

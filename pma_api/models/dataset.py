import os


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
    data = db.Column(db.LargeBinary)
    datasetDisplayName = db.Column(db.String, nullable=False)
    uploadDate = db.Column(db.String, nullable=False)
    versionNumber = db.Column(db.String, nullable=False, unique=True)
    datasetType = db.Column(db.String, nullable=False)
    isActiveStaging = db.Column(db.Boolean, nullable=False)
    isActiveProduction = db.Column(db.Boolean, nullable=False)

    def __init__(self, file_path):
        """Initialize instance of dataset"""
        data = open(file_path, 'r')
        data2 = data.read()

        datasetDisplayName = os.path.basename(file_path)
        naming = datasetDisplayName.split('-')
        uploadDate = naming[1]
        versionNumber = naming[2]
        datasetType = 'full'
        isActiveStaging = False
        isActiveProduction = False

        super(Dataset, self).__init__(
            data=data,
            datasetDisplayName=datasetDisplayName,
            uploadDate=uploadDate,
            versionNumber=versionNumber,
            datasetType=datasetType,
            isActiveStaging=isActiveStaging,
            isActiveProduction=isActiveProduction
        )

        data.close()


    @classmethod
    def get(cls, ID):
        """Return a record by ID."""
        return cls.query.filter_by(ID=ID).first()

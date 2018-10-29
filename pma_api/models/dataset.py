"""Dataset model."""
import datetime
# from hashlib import md5
import os

from . import db


class Dataset(db.Model):
    """
    dataset_type: string / varchar; factor var of ('data', 'metadata', 'full')
    datasetSubType: string / varchar ~256?; domain of,
    ('CCRR', 'METADATA_CLASS', 'all'/'full')

    Example usage:
           new_dataset = Dataset(file_path)
    """
    __tablename__ = 'dataset'
    ID = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.LargeBinary)
    dataset_display_name = db.Column(db.String, nullable=False)
    upload_date = db.Column(db.String, nullable=False)
    version_number = db.Column(db.String, nullable=False, unique=True)
    dataset_type = db.Column(db.String, nullable=False)
    is_active_staging = db.Column(db.Boolean, nullable=False)
    is_active_production = db.Column(db.Boolean, nullable=False)

    def __init__(self, file_path):
        """Initialize instance of dataset"""
        data_file = open(file_path, 'rb').read()
        dataset_display_name = os.path.basename(file_path)
        naming = dataset_display_name.split('-')
        upload_date = datetime.date.today()
        version_number = naming[2]
        dataset_type = 'full'
        is_active_staging = False
        is_active_production = False

        super(Dataset, self).__init__(
            data=data_file,
            dataset_display_name=dataset_display_name,
            upload_date=upload_date,
            version_number=version_number,
            dataset_type=dataset_type,
            is_active_staging=is_active_staging,
            is_active_production=is_active_production)

    @classmethod
    def get(cls, _id):
        """Return a record by ID."""
        return cls.query.filter_by(ID=_id).first()

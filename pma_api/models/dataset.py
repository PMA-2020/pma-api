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
    is_active = db.Column(db.Boolean, nullable=False)
    is_processing = db.Column(db.Boolean, nullable=False)
    is_active_staging = db.Column(db.Boolean, nullable=False)
    is_active_production = db.Column(db.Boolean, nullable=False)
    is_processing_staging = db.Column(db.Boolean, nullable=False)
    is_processing_production = db.Column(db.Boolean, nullable=False)

    def __init__(self, file_path):
        """Initialize instance of dataset"""
        dataset_display_name = os.path.basename(file_path)

        super(Dataset, self).__init__(
            data=open(file_path, 'rb').read(),
            dataset_display_name=dataset_display_name,
            upload_date=datetime.date.today(),
            version_number=dataset_display_name.split('-')[2],
            dataset_type='full',  # TODO: allow for different types
            is_active=False,
            is_processing=False,
            is_active_staging=False,
            is_active_production=False,
            is_processing_staging=False,
            is_processing_production=False)

    @classmethod
    def get(cls, _id):
        """Return a record by ID."""
        return cls.query.filter_by(ID=_id).first()

    def register_active(self):
        """Register dataset as being actively in use in the database

        If 'is_active' is true, the contents of this dataset will be present
        in database tables. If false, the dataset itself is stored as a binary
        file in the database, but none of its contents appear in any of the
        other tables.
        """
        pass

    def register_processing(self):
        """Register dataset as being actively processed; being applied to db"""
        pass

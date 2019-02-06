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
    version_number = db.Column(db.Integer, nullable=False, unique=True)
    dataset_type = db.Column(db.String, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False)
    is_processing = db.Column(db.Boolean, nullable=False)

    def __init__(self, file_path: str, is_processing: bool = False):
        """Initialize instance of dataset

        Args:
            file_path (str): Path to dataset file
            is_processing (bool): Is this dataset currently being uploaded?
        """
        dataset_display_name: str = os.path.basename(file_path)

        version: int = \
            int(str(dataset_display_name.split('-')[2]).replace('v', ''))

        super(Dataset, self).__init__(
            data=open(file_path, 'rb').read(),
            dataset_display_name=dataset_display_name,
            upload_date=datetime.date.today(),
            version_number=version,
            dataset_type='full',  # TODO: allow for different types
            is_active=False,
            is_processing=is_processing)

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
        Dataset.query.filter_by(ID=self.ID).update({
            'is_active': True,
            'is_processing': False})
        db.session.commit()

    def register_processing(self):
        """Register dataset as being actively processed; being applied to db"""
        Dataset.query.filter_by(ID=self.ID).update({
            'is_active': False,
            'is_processing': True})
        db.session.commit()

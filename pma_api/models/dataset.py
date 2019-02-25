"""Dataset model."""
import datetime
import os
import sys
from sqlalchemy.exc import IntegrityError
from typing import List

from pma_api.config import ACCEPTED_DATASET_EXTENSIONS as EXTENSIONS
from pma_api.models import db


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
        path_with_ext: str = file_path if \
            any(file_path.endswith('.' + x) for x in EXTENSIONS) \
            else file_path + '.xlsx'

        # with ext:
        filename: str = os.path.basename(path_with_ext)
        # without ext:
        # filename: str = os.path.splitext(os.path.basename(path_with_ext))[0]

        filename_parts: list = filename.split('-')
        dataset_display_name: str = filename_parts[0]

        version_str: str = filename_parts[2]
        for ext in EXTENSIONS:
            suffix: str = '.' + ext
            if version_str.endswith(suffix):
                version_str = version_str.replace(suffix, '')
                break
        version: int = int(version_str.replace('v', '') if 'v' in version_str
                           else version_str)

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

    @classmethod
    def process_new(cls, path: str):
        """Upload new dataset if does not exist, and register processing

        Args:
            path (str): Path to a dataset to be initialized and registered

        Returns:
            dataset (Dataset): The dataset registered as processing
            warning (str): Warning message, if any.
        """
        warning: str = ''
        dataset: Dataset = Dataset(file_path=path, is_processing=True)
        try:
            db.session.add(dataset)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            warning: str = (
                'Warning: During DB initialization, it was found that a '
                'dataset with version number {} has already been previously '
                'uploaded to the database. Using that instead of the '
                'dataset which was found in the file system: \n' + path +
                '\n\n' +
                'If there is any doubt that the dataset on the file system '
                'is different/newer than the one previously uploaded, then '
                'please increment the version number of the dataset shown, '
                'and try again.'.format(dataset.version_number))
            dataset: Dataset = Dataset.query.filter_by(
                version_number=dataset.version_number).first()

        return dataset, warning

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
        dataset: Dataset = Dataset.query.filter_by(ID=self.ID)
        dataset.update({'is_active': False, 'is_processing': True})
        db.session.commit()

    @staticmethod
    def register_all_inactive():
        """Register all datasets as inactive

        Used during database initialization
        """
        datasets: List[Dataset] = Dataset.query.filter_by(is_active=True)
        for dataset in datasets:
            dataset.is_active = False

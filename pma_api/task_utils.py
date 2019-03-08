"""Utilities for tasks"""
import json
import os
from io import BytesIO
from json import JSONDecodeError

from sqlalchemy.exc import IntegrityError
from typing import Dict

import requests
from flask import current_app
from werkzeug.datastructures import FileStorage

from pma_api import create_app
from pma_api.config import data_folder_path, temp_folder_path, \
    ACCEPTED_DATASET_EXTENSIONS as EXTENSIONS, ACCEPTED_DATASET_EXTENSIONS
from pma_api.error import PmaApiException
from pma_api.models import Dataset
from pma_api.routes.administration import ExistingDatasetError

try:
    app = current_app
    if app.__repr__() == '<LocalProxy unbound>':
        raise RuntimeError('A current running app was not able to be found.')
except RuntimeError:
    app = create_app(os.getenv('ENV_NAME', 'default'))


def save_file_from_request(file: FileStorage, file_path: str):
    """Save file at a specific location.

    Args:
        file (FileStorage): File.
        file_path (str): File name.

    Raises:
        PmaApiException: If file saved is 0 bytes
    """
    if not os.path.exists(os.path.dirname(file_path)):
        os.mkdir(os.path.dirname(file_path))
    file.save(file_path)
    file.close()

    if os.path.getsize(file_path) == 0:
        raise PmaApiException('File saved, but was 0 bytes.\n- Path: {}'
                              .format(file_path))


def file_path_from_dataset_name(dataset_name: str,
                                directory: str = data_folder_path()):
    """From a dataset name, get the path where it should exist locally

    Args:
        dataset_name (str): Name of dataset, which may or may not include file
          extension
        directory (str): Directory where local file should exist

    Returns:
        str: Path to file
    """
    filename: str = dataset_name if \
        any(dataset_name.endswith('.' + x) for x in EXTENSIONS) \
        else dataset_name + '.xlsx'
    file_path: str = os.path.join(directory, filename)

    return file_path


def download_dataset_from_db(dataset_id: str,
                             directory: str = data_folder_path()):
    """Download dataset from database to filesystem

    Args:
        dataset_id (str): Name of dataset file to look up in db
        directory (str): Directory to save file

    Returns:
        str: Path to downloaded dataset file
    """
    file_path: str = file_path_from_dataset_name(dataset_name=dataset_id,
                                                 directory=directory)
    replace_file: bool = True if os.path.exists(file_path) else False

    if replace_file:
        os.remove(file_path)

    with app.app_context():
        dataset: Dataset = \
            Dataset.query.filter_by(dataset_display_name=dataset_id)\
            .first()
    save_file_from_bytes(file_bytes=dataset.data, file_path=file_path)

    return file_path


def save_file_from_bytesio(file: BytesIO, file_path: str, _attempt: int = 1):
    """Save file at a specific location.

    Args:
        file (BytesIO): File.
        file_path (str): File name.
        _attempt (int): Attempt number for trying to save file.
    """
    max_attempts = 2
    try:
        with open(file_path, 'wb') as f:
            f.write(file.read())
        f.close()

    except FileNotFoundError:
        os.mkdir(os.path.dirname(file_path))
        if _attempt < max_attempts:
            save_file_from_bytesio(file=file, file_path=file_path,
                                   _attempt=_attempt + 1)


def save_file_from_bytes(file_bytes: bytes, file_path: str,
                         _attempt: int = 1):
    """Save file_bytes at a specific location.

    Args:
        file_bytes (bytes): File bytes.
        file_path (str): File name.
        _attempt (int): Attempt number for trying to save file_bytes.
    """
    max_attempts = 2
    try:
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        f.close()

    except FileNotFoundError:
        os.mkdir(os.path.dirname(file_path))
        if _attempt < max_attempts:
            save_file_from_bytes(file_bytes=file_bytes, file_path=file_path,
                                 _attempt=_attempt + 1)


def load_local_dataset(dataset_name: str) -> FileStorage:
    """Load a dataset that exists in local database

    Args:
        dataset_name (str): Name of dataset that should exist in db

    Returns:
        werkzeug.datastructures.FileStorage: In-memory file, in bytes
    """
    file_path: str = file_path_from_dataset_name(dataset_name=dataset_name,
                                                 directory=data_folder_path())
    save_temporarily: bool = False if os.path.exists(file_path) else True

    if save_temporarily:
        download_dataset_from_db(dataset_id=dataset_name)

    data: FileStorage = open(file_path, 'rb')

    if save_temporarily:
        os.remove(file_path)

    return data


def upload(filename: str, file):
    """Upload file into database

    Args:
        filename (str): File name.
        file: File.

    Raises:
        ExistingDatasetError: If dataset already exists
    """
    from pma_api.models import Dataset, db

    default_ext = 'xlsx'
    has_ext: bool = any(filename.endswith(x) for x in
                        ACCEPTED_DATASET_EXTENSIONS)
    filename_with_ext: str = filename if has_ext \
        else filename + '.' + default_ext
    tempfile_path: str = os.path.join(temp_folder_path(), filename_with_ext)
    save_file_from_request(file=file, file_path=tempfile_path)

    new_dataset = Dataset(tempfile_path)
    db.session.add(new_dataset)
    try:
        db.session.commit()
    except IntegrityError as err:
        db.session.rollback()
        if 'already exists' in str(err):
            msg = 'Error: A dataset named "{}" already exists in DB.'\
                .format(filename)
            raise ExistingDatasetError(msg)
        else:
            raise err
    finally:
        if os.path.exists(tempfile_path):
            os.remove(tempfile_path)


def response_to_task_state(r: requests.Response) -> Dict:
    """Convert response object to custom task state dictionary.

    Args:
        r (requests.Response): Response object

    Returns:
        dict: Custom task state
    """
    data: Dict
    try:
        data: Dict = json.loads(r.text)
    except JSONDecodeError as err:  # TODO: Why is this happening? What to do?
        if r.status_code != 500:  # Server error
            raise err
        data['state'] = 'FAILURE'
        data['status'] = 'Internal server error'
        data['current'] = str(0)
        data['total'] = str(100)

    state = {
        'state': data['state'] if 'state' in data else '',
        'status': data['status'] if 'status' in data else '',
        'current': data['current'] if 'current' in data else '',
        'total': data['total'] if 'total' in data else '',
        'http': {
            'status_code': r.status_code,
            'status_reason': r.reason}}

    return state


def progress_update_callback(celery_obj, verbose=False):
    """Progress update callback

    Args:
        celery_obj: Celery object
        verbose (bool): Print update yields?

    Side effects:
        celery_obj.update_state: Updates task state.
    """
    while True:
        update_obj = yield
        status, current = update_obj['status'], update_obj['current']
        if verbose:
            percent: str = str(int(current * 100)) + '%'
            print('{} ({})'.format(status, percent))
        celery_obj.update_state(state='PROGRESS', meta={
            'status': status,
            'current': current,
            'total': 100})  # TODO: May cause issue if total is not pct based

"""Utilities for tasks"""
import json
import os
from io import BytesIO
from json import JSONDecodeError

from typing import Dict, List, BinaryIO, Union

import requests
from celery import Celery
from flask import current_app
from werkzeug.datastructures import FileStorage

from pma_api import create_app
from pma_api.config import temp_folder_path, \
    ACCEPTED_DATASET_EXTENSIONS as EXTENSIONS, S3_DATASETS_DIR_PATH, \
    AWS_S3_STORAGE_BUCKETNAME as BUCKET
from pma_api.error import PmaApiException
from pma_api.manage.db_mgmt import download_dataset
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


def load_local_dataset_from_db(dataset_id: str) -> BinaryIO:
    """Load a dataset that exists in local database

    Side effects:
        - download_dataset_from_db()
        - Reads file

    Args:
        dataset_id (str): ID of dataset that should exist in db

    Returns:
        werkzeug.datastructures.FileStorage: In-memory file, in bytes
    """
    file_path: str = download_dataset(int(dataset_id))
    data: BinaryIO = open(file_path, 'rb')

    return data


def upload_dataset(filename: str, file) -> str:
    """Upload file to data storage

    Args:
        filename (str): File name.
        file: File.

    Side effects:
        - Stores file on AWS S3 using: store_file_on_s3

    Raises:
        ExistingDatasetError: If dataset already exists

    Returns:
        str: Url where file is stored
    """
    from pma_api.manage.db_mgmt import store_file_on_s3, list_cloud_datasets
    from pma_api.models import Dataset

    # 1. Save file
    default_ext = 'xlsx'
    has_ext: bool = any(filename.endswith(x) for x in EXTENSIONS)
    filename_with_ext: str = filename if has_ext \
        else filename + '.' + default_ext
    tempfile_path: str = os.path.join(temp_folder_path(), filename_with_ext)

    save_file_from_request(file=file, file_path=tempfile_path)

    # 2. Validate
    this_dataset: Dataset = Dataset(tempfile_path)
    this_version: int = this_dataset.version_number
    uploaded_datasets: List[Dict[str, str]] = list_cloud_datasets()
    uploaded_versions: List[int] = \
        [int(x['version_number']) for x in uploaded_datasets]
    already_exists: bool = this_version in uploaded_versions

    if already_exists:
        msg = 'ExistingDatasetError: Dataset version "{}" already exists.'\
            .format(str(this_version))
        if os.path.exists(tempfile_path):
            os.remove(tempfile_path)
        raise ExistingDatasetError(msg)

    # 3. Upload file
    filename: str = store_file_on_s3(
        path=tempfile_path,
        storage_dir=S3_DATASETS_DIR_PATH)

    # 4. Closeout
    if os.path.exists(tempfile_path):
        os.remove(tempfile_path)
    file_url = 'https://{bucket}.s3.amazonaws.com/{path}{object}'.format(
        bucket=BUCKET,
        path=S3_DATASETS_DIR_PATH,
        object=filename)

    return file_url


# TODO: Is this code even used?
def response_to_task_state(r: requests.Response) -> Dict:
    """Convert response object to custom task state dictionary.

    Args:
        r (requests.Response): Response object

    Returns:
        dict: Custom task state
    """
    try:
        data: Dict = json.loads(r.text)
    except JSONDecodeError as err:  # TODO: Why is this happening? What to do?
        if r.status_code != 500:  # Server error
            raise err
        data = {
            'state': 'FAILURE',
            'status': 'Internal server error',
            'current': str(0),
            'total': str(100)}

    state = {
        'state': data['state'] if 'state' in data else '',
        'status': data['status'] if 'status' in data else '',
        'current': data['current'] if 'current' in data else '',
        'total': data['total'] if 'total' in data else '',
        'http': {
            'status_code': r.status_code,
            'status_reason': r.reason}}

    return state


def progress_update_callback(task_obj: Celery, verbose: bool = False):
    """Progress update callback generator

    Side effects:
        - task_obj.update_state(): Updates task state.
        - print(): if verbose

    Args:
        task_obj (Celery): Celery task object
        verbose (bool): Print update yields?
    """
    while True:
        # 1. Receive update via progress_update_callback.send()
        # noinspection PyUnusedLocal
        update_obj: Dict[str, Union[str, float]]
        update_obj = yield

        # 2. Set some static variables
        status: str = update_obj['status'] if 'status' in update_obj else ''
        current: Union[float, int] = update_obj['current'] \
            if 'current' in update_obj else 0
        total: int = update_obj['total'] if 'total' in update_obj \
            else 100 if current and current > 1 else 1

        # 3. Create report
        static_report: Dict[str, Union[str, float, int]] = {
            'status': status,
            'current': current,
            'total': total}
        dynamic_report: Dict = {
            k: v
            for k, v in update_obj.items()
            if k not in static_report.keys()}
        report: Dict = {**static_report, **{'args': dynamic_report}} \
            if dynamic_report else static_report

        # 4. Send report
        if verbose:
            percent: str = str(int(current * 100)) + '%'
            print('{} ({})'.format(status, percent))
        task_obj.update_state(state='PROGRESS', meta=report)

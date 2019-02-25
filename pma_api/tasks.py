"""Tasks

# TODO: Add dynamic routing for each celery task, like from db.Model
"""
import json
import os
import time
from io import BytesIO

from sqlalchemy.exc import IntegrityError
from typing import Dict

import requests
from celery import Celery
from flask import current_app
from werkzeug.datastructures import FileStorage

from pma_api import create_app
from pma_api.config import data_folder_path, temp_folder_path, \
    ACCEPTED_DATASET_EXTENSIONS as EXTENSIONS, \
    ASYNC_SECONDS_BETWEEN_STATUS_CHECKS as TICK_SECONDS
from pma_api.error import PmaApiException
from pma_api.manage.db_mgmt import initdb_from_wb
from pma_api.models import Dataset
from pma_api.routes.administration import ExistingDatasetError
from pma_api.utils import join_url_parts

try:
    app = current_app
    celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
except RuntimeError:
    app = create_app(os.getenv('ENV_NAME', 'default'))
    celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)


CELERY_COMPLETION_CODES = ('FAILURE', 'SUCCESS')


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


def download_dataset_from_db(dataset_name: str,
                             directory: str = data_folder_path()):
    """Download dataset from database to filesystem

    Args:
        dataset_name (str): Name of dataset file to look up in db
        directory (str): Directory to save file

    Returns:
        str: Path to downloaded dataset file
    """
    file_path: str = file_path_from_dataset_name(dataset_name=dataset_name,
                                                 directory=directory)
    replace_file: bool = True if os.path.exists(file_path) else False

    if replace_file:
        os.remove(file_path)

    with app.app_context():
        dataset: Dataset = \
            Dataset.query.filter_by(dataset_display_name=dataset_name)\
            .first()
    save_file_from_bytes(file_bytes=dataset.data, file_path=file_path)

    return file_path


def save_file_from_bytesio(file: BytesIO, file_path: str, attempt: int = 1):
    """Save file at a specific location.

    Args:
        file (BytesIO): File.
        file_path (str): File name.
        attempt (int): Attempt number for trying to save file.
    """
    max_attempts = 2
    try:
        with open(file_path, 'wb') as f:
            f.write(file.read())
        f.close()

    except FileNotFoundError:
        os.mkdir(os.path.dirname(file_path))
        if attempt < max_attempts:
            save_file_from_bytesio(file=file, file_path=file_path,
                                   attempt=attempt+1)


def save_file_from_bytes(file_bytes: bytes, file_path: str,
                         attempt: int = 1):
    """Save file_bytes at a specific location.

    Args:
        file_bytes (bytes): File bytes.
        file_path (str): File name.
        attempt (int): Attempt number for trying to save file_bytes.
    """
    max_attempts = 2
    try:
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        f.close()

    except FileNotFoundError:
        os.mkdir(os.path.dirname(file_path))
        if attempt < max_attempts:
            save_file_from_bytes(file_bytes=file_bytes, file_path=file_path,
                                 attempt=attempt+1)


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
        download_dataset_from_db(dataset_name=dataset_name)

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

    tempfile_path: str = os.path.join(temp_folder_path(), filename)
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
    data: Dict = json.loads(r.text)

    state = {
        'state': data['state'] if 'state' in data else '',
        'status': data['status'] if 'status' in data else '',
        'current': data['current'] if 'current' in data else '',
        'total': data['total'] if 'total' in data else '',
        'http': {
            'status_code': r.status_code,
            'status_reason': r.reason}}

    return state


def progress_update_callback(celery_obj: celery.task, verbose=False):
    """Progress update callback

    Args:
        celery_obj (celery.task): Celery object
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
            'total': 100})


@celery.task(bind=True)  # TODO: temp
def long_task(self):
    """Background task that runs a long function with progress reports."""
    import random

    verb = ['Starting up', 'Booting', 'Repairing', 'Loading', 'Checking']
    adjective = ['master', 'radiant', 'silent', 'harmonic', 'fast']
    noun = ['solar array', 'particle reshaper', 'cosmic ray', 'orbiter',
            'bit']
    message = ''
    total = random.randint(10, 50)

    callback = progress_update_callback(celery_obj=self, verbose=True)
    next(callback)

    for i in range(total):
        if not message or random.random() < 0.25:
            message = '{0} {1} {2}...'.format(random.choice(verb),
                                              random.choice(adjective),
                                              random.choice(noun))
        callback.send({'status': message, 'current': i})
        time.sleep(0.1)

    callback.close()
    return {'current': 100, 'total': 100, 'status': 'Task completed!'}


@celery.task(bind=True)  # TODO: fix action_url when works
def activate_dataset_request(self, dataset_name: str,
                             destination_host_url: str,
                             dataset: FileStorage = None) -> Dict:
    """Activate dataset to be uploaded and actively used on target server.

    Args:
        dataset_name (str): Name of dataset to send.
        destination_host_url (str): URL of server to apply dataset.

    Side effects:
        self: Updates state.

    Returns:
        dict: Results.

    TODO: Split upload & run db script into 2
    """
    action_route = 'activate_dataset'
    # action_url: str = join_url_parts(destination_host_url, action_route)
    action_url: str = join_url_parts('http://localhost:5000', action_route)
    post_data: FileStorage = \
        dataset if dataset else load_local_dataset(dataset_name)

    r = requests.post(action_url, files={dataset_name: post_data})
    state: Dict = response_to_task_state(r)

    self.update_state(state=state['state'], meta=state)
    if state['state'] in CELERY_COMPLETION_CODES:
        return state

    status_route: str = r.headers['Content-Location']
    status_url: str = join_url_parts(destination_host_url, status_route)
    while True:
        r = requests.get(status_url)
        state: Dict = response_to_task_state(r)
        self.update_state(state=state['state'], meta=state)

        if state['state'] in CELERY_COMPLETION_CODES:
            break

        time.sleep(TICK_SECONDS)

    return state


@celery.task(bind=True)
def activate_dataset_to_self(self, dataset_name: str) -> Dict:
    """Activate dataset to the this server.

    Args:
        dataset_name (str): Name of dataset.

    Returns:
        dict: Results.
    """
    callback = progress_update_callback(celery_obj=self, verbose=True)
    next(callback)

    file_path: str = download_dataset_from_db(
        dataset_name=dataset_name,
        directory=data_folder_path())

    app.config.SQLALCHEMY_ECHO = False  # TODO: temp
    # TODO: with incremental uploads, set overwrite=False unless an
    #  overwrite param is specified (can add to admin portal ui)
    initdb_from_wb(
        callback=callback,
        api_file_path=file_path,
        overwrite=True,
        _app=app)

    callback.close()
    return {'current': 100, 'total': 100, 'status': 'Completed'}

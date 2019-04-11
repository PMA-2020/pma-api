"""Utilities for tasks

TODOs:
    1. 2019.04.16-jef: A better structure for this and 'tasks' module would be
    to make a 'tasks' subpackage folder, put 'tasks' in __init__.py, and put
    this file into a new file there called 'utils'.
"""
import os
import time
from io import BytesIO

from typing import Dict, List, BinaryIO, Union

from celery import Celery
from celery.exceptions import NotRegistered
from celery.result import AsyncResult
from werkzeug.datastructures import FileStorage

from pma_api.config import TEMP_DIR, \
    ACCEPTED_DATASET_EXTENSIONS as EXTENSIONS, S3_DATASETS_DIR_PATH, \
    AWS_S3_STORAGE_BUCKETNAME as BUCKET, PACKAGE_DIR_NAME, CELERY_QUEUE
from pma_api.error import PmaApiException
from pma_api.manage.db_mgmt import download_dataset
from pma_api.routes.administration import ExistingDatasetError
from pma_api.utils import get_app_instance


app = get_app_instance()


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
    tempfile_path: str = os.path.join(TEMP_DIR, filename_with_ext)

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


def _get_task_status_report(task_id: str) -> Dict[str, Union[str, int, float]]:
    """Get task status report as custom dictionary

    Args:
        task_id (str): Task id

    Returns:
        dict(Union[str,int,float]: Custom task status report
    """
    from pma_api.tasks import celery as celery_instance

    err = 'Server: Unexpected error occurred while processing task.'
    task: Union[AsyncResult, NotRegistered] = \
        celery_instance.AsyncResult(task_id)
    state: str = task.state
    dynamic_report = {}

    # noinspection PyTypeChecker
    info: Union[Dict, NotRegistered, Exception] = task.info
    info_available: bool = \
        info is not None and not isinstance(info, NotRegistered)

    if isinstance(info, Exception):
        # TODO: [Errno 2] No such file or directory  -- being reported here
        #  - why?
        exc: Exception = info
        static_report: Dict[str, Union[str, int]] = {
            'id': task_id,
            'url': '',
            'state': state,
            'status': str(exc),
            'current': 0,
            'total': 1,
            'result': state}  # to-do: remove all instances of 'result'?}
    elif state == 'FAILURE':
        # to-do: I know I can receive tuple when fail, but not sure what type
        # 'task' is in that case
        # noinspection PyUnresolvedReferences
        info2: tuple = info.args
        status: str = '' if not info2 \
            else info2[0] if isinstance(info2, tuple) and len(info2) == 1 \
            else str(list(info2))

        # For some reason, unknown failures can happen. When this happens,
        # the module path is displayed, e.g.: 'pma_api.tasks.activate_dataset'
        status: str = \
            status if not status.startswith(PACKAGE_DIR_NAME) else err

        static_report: Dict[str, Union[str, int]] = {
            'id': task_id,
            'url': '',
            'state': state,
            'status': status,
            'current': 0,
            'total': 1,
            'result': state}  # to-do: remove all instances of 'result'?}
    else:
        # TODO: state and status == 'PENDING'. Why?
        # pg_restore: [archiver (db)] Error while PROCESSING TOC:
        # pg_restore: [archiver (db)] Error from TOC entry 2470; 1262 197874
        # DATABASE pmaapi postgres
        # pg_restore: [archiver (db)] could not execute query: ERROR:
        # database "pmaapi" is being accessed by other users
        # DETAIL:  There are 2 other sessions using the database.
        #     Command was: DROP DATABASE pmaapi;
        #
        # Offending command: pg_restore --exit-on-error --create --clean
        # --dbname=postgres --host=localhost --port=5432 --username=postgres
        # /Users/joeflack4/projects/pma-api/data/db_backups/pma-api-backup_Mac
        # OS_development_2019-04-04_13-04-54.568706.dump

        status: str = \
            info['status'] if info_available and 'status' in info else state
        current: Union[int, float] = \
            info['current'] if info_available and 'current' in info else 0
        total: int = \
            info['total'] if info_available and 'total' in info else 1
        static_report: Dict[str, Union[str, int, float]] = {
            'id': task_id,
            'url': '',
            'state': state,
            'status': status,
            'current': current,
            'total': total}

        # noinspection PyBroadException
        try:  # TO-DO 1
            dynamic_report: Dict = info['args']
        except Exception:
            pass

    report: Dict[str, Union[str, int, float]] = {
        **static_report,
        **dynamic_report}

    return report


def get_task_status(
        task_id: str, return_format: str = 'str', attempt: int = 1) -> \
        Union[str, Dict[str, Union[str, int, float]]]:
    """Get task status from message broker through celery

    TODO 2019.04.16-jef: Maybe the restarting of this shouldn't happen at this
     level, but at the level of routing, or wherever the root source of the
     request is coming from.

    Args:
        task_id (str): Task id
        return_format (str): Can be 'str' or 'dict'. If 'str', will return
         celery's default single-word task state. Else if 'dict', will return a
         custom dictionary.
        attempt (int): Attempt number

    Raises:
        PmaApiException: If 'format' arg passed is not in valid.

    Returns:
        Union[str,Dict]: See arg 'format' for more info
    """
    from pma_api.tasks import celery as celery_instance

    max_attempts: int = 15
    sleep_secs: int = 1
    err = 'Call to get task status did not request in a valid format.\n' \
        '- Format requested: {}\n' \
        '- Valid formats: str, dict'.format(return_format)

    if return_format == 'str':
        task: Union[AsyncResult, NotRegistered] = \
            celery_instance.AsyncResult(task_id)
        try:
            status: str = task.state
        # 2019.04.16-jef: Not sure what caused BrokenPipeError; maybe was a
        # server restart?
        except BrokenPipeError as exc:
            if attempt < max_attempts:
                time.sleep(sleep_secs)
                return get_task_status(
                    task_id=task_id,
                    return_format=return_format,
                    attempt=attempt+1)
            else:
                raise exc
    elif return_format == 'dict':
        status: Dict[str, Union[str, int, float]] = \
            _get_task_status_report(task_id)
    else:
        raise PmaApiException(err)

    return status


def validate_active_task_status(task_id: str) -> bool:
    """Validate task status

    Args:
        task_id (str): Celery task ID

    Returns:
        bool: True if task is actually active, else False.
    """
    from pma_api.tasks import CELERY_COMPLETION_CODES

    status_code: str = get_task_status(task_id)

    return False if status_code in CELERY_COMPLETION_CODES else True


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


def start_task(
        func: Celery, kwarg_dict: Dict = None, queue: str = CELERY_QUEUE) \
        -> str:
    """Start a task, handling unexplaiend failures along the way

    Args:
        func (Celery): Celery task function to call to start task
        kwarg_dict (dict): Dicitonary to pass to Celery.apply_async's single
         kwargs parameter
        queue (str): Name of the celery queue to use

    Returns:
        str: Task ID
    """
    task: AsyncResult = func.apply_async(
        kwargs=kwarg_dict if kwarg_dict else {},
        queue=queue)
    task_id: str = task.id

    return task_id

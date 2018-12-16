"""Tasks"""
import json
import os
from io import BytesIO

import celery
import requests
from werkzeug.datastructures import FileStorage

from pma_api.manage.db_mgmt import initdb_from_wb
from pma_api.config import data_folder_path, temp_folder_path
from pma_api.models import Dataset
from pma_api.routes.root_routes import upload, ExistingDatasetError

APPLY_DATASET_ROUTE = 'apply_dataset'


# I. Sending server
#   1. Set dataset's 'is_processing_staging/production' attr
#   to True.
#   2. On web page, give user notification that upload is in
#   progress. Tjos takes time and requires page refresh
#   3. Receive results when receiving server sends back a
#   notification of upload results.
#   4. Bciar: Automatically refresh page when receive results.
# II. Receiving server
#   1. Receives the file at the /upload route
#   2. Runs manage.py initdb --overwrite
#   3. Sends results (success/fail) to sending server
def save_file_from_request(file: FileStorage, file_path: str):
    """Save file at a specific location.

    Args:
        file (FileStorage): File.
        file_path (str): File name.
    """
    try:
        file.save(file_path)
        file.close()
    except FileNotFoundError:
        os.mkdir(os.path.dirname(file_path))
        file.save(file_path)
        file.close()
    # check if file is 0 bytes ?
    # fileio = file.stream.raw
    # print(fileio)


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
            # Getting an Excel File represented as a BytesIO Object
            f.write(file.read())
        f.close()
        # temporarylocation = "testout.xlsx"
        # # Open temporary file as bytes
        # with open(temporarylocation, 'wb') as out:
        #     out.write(g.read())

    except FileNotFoundError:
        os.mkdir(os.path.dirname(file_path))
        if attempt < max_attempts:
            save_file_from_bytesio(file=file, file_path=file_path,
                                   attempt=attempt+1)


def save_file_from_bytes(file_bytes: bytes, file_path: str, attempt: int = 1):
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


@celery.task(bind=True)
def apply_dataset_request(self, dataset_name: str, destination: str) -> dict:
    """Applies a dataset to be uploaded and actively used on target server.

    Args:
        dataset_name (str): Name of dataset to send.
        destination (str): URL of server to apply dataset.

    Side effects:
        self: Updates state.

    Returns:
        dict: Results.

    TODO: Split upload & run db script into 2
    """
    # temp safetey-net:
    print(destination)
    # action_url = destination + '/' + APPLY_DATASET_ROUTE

    action_url = 'http://localhost:5000' + '/' + APPLY_DATASET_ROUTE
    #
    dataset_obj = Dataset.query.filter_by(
        dataset_display_name=dataset_name).first()
    file_path = os.path.join(temp_folder_path(), dataset_name)
    save_file_from_bytes(file_bytes=dataset_obj.data, file_path=file_path)
    #

    r = requests.post(action_url, files={dataset_name:  open(file_path, 'rb')})
    result = json.loads(r.text)
    # print(r.status_code, r.reason, r.text[:300])
    self.update_state(state='PROGRESS',
                      meta={'status': result})

    # db script finishes and state updates accordingly
    # this is done by target server?
    # self.update_state(state='PROGRESS',
    #                   meta={'status': 'placeholder'})

    return {'status': result}


@celery.task(bind=True)
def apply_dataset_to_self(self, dataset_name, dataset: FileStorage) -> dict:
    """Applies a dataset to the this server.

    Args:
        dataset_name (str): Name of dataset.
        dataset (FileStorage): Dataset to apply.

    Side effects:
        self: Updates state.

    Returns:
        dict: Results.

    """
    # from run import app

    upload_success = False
    try:
        # replace "upload" w/ a url call
        upload(filename=dataset_name, file=dataset)

        details = {'message': 'Uploaded dataset. Apply dataset pending.'}
        self.update_state(state='PROGRESS', meta={'status': details})
        upload_success = True
    except ExistingDatasetError:
        details = {'message': 'Dataset exists. Apply dataset pending.'}
        self.update_state(state='ERROR', meta={'status': details})
        upload_success = True
    except Exception as err:
        msg = 'An unexpected error occurred:\n\n' + str(err)
        details = {'message': msg}
        self.update_state(state='ERROR', meta={'status': details})

    # if upload_success:
    #     dataset_obj = Dataset.query.filter_by(
    #         dataset_display_name=dataset_name).first()
    #     file_path = os.path.join(data_folder_path(), dataset_name)
    #     save_file_from_bytes(file_bytes=dataset_obj.data, file_path=file_path)
    #     result = initdb_from_wb(overwrite=True, api_data=file_path,
    #                             _app=app)
    #     details = {'message': result}
    print(upload_success)

    # Always returns 'none' for some reason:
    # status = self.AsyncResult(self.request.id).state
    return details

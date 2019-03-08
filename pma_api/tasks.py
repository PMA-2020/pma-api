"""Tasks

# TODO: Add dynamic routing for each celery task, like from db.Model
"""
import os
import time

from typing import Dict

import requests
from celery import Celery
from flask import current_app
from werkzeug.datastructures import FileStorage

from pma_api import create_app
from pma_api.config import data_folder_path, \
    ASYNC_SECONDS_BETWEEN_STATUS_CHECKS as TICK_SECONDS
from pma_api.manage.db_mgmt import initdb_from_wb
from pma_api.utils import join_url_parts
from pma_api.task_utils import progress_update_callback, load_local_dataset, \
    response_to_task_state, download_dataset_from_db

try:
    app = current_app
    if app.__repr__() == '<LocalProxy unbound>':
        raise RuntimeError('A current running app was not able to be found.')
    celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
except RuntimeError:
    app = create_app(os.getenv('ENV_NAME', 'default'))
    celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)


CELERY_COMPLETION_CODES = ('FAILURE', 'SUCCESS')


@celery.task(bind=True)  # TODO: temp
def long_task(self):
    """Background task that runs a long function with progress reports.

    Args:
        self (Celery.task): Required Celery obj ref. Not to be used as param.
    """
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
    return {'current': total, 'total': total, 'status': 'Task completed!'}


@celery.task(bind=True)  # TODO: fix action_url when works
def activate_dataset_request(self, dataset_id: str,
                             destination_host_url: str,
                             dataset: FileStorage = None) -> Dict:
    """Activate dataset to be uploaded and actively used on target server.

    Args:
        self (Celery.task): Required Celery obj ref. Not to be used as param.
        dataset_id (str): Name of dataset to send.
        destination_host_url (str): URL of server to apply dataset.
        dataset (FileStorage): Optional dataset object

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
        dataset if dataset else load_local_dataset(dataset_id)

    r = requests.post(action_url, files={dataset_id: post_data})
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
def activate_dataset_to_self(self, dataset_id: str) -> Dict:
    """Activate dataset to the this server.

    Args:
        self (Celery.task): Required Celery obj ref. Not to be used as param.
        dataset_id (str): Name of dataset.

    Returns:
        dict: Results.
    """
    callback = progress_update_callback(celery_obj=self, verbose=True)
    next(callback)

    file_path: str = download_dataset_from_db(
        dataset_id=dataset_id,
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

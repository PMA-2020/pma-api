"""Tasks

# TODO: Add dynamic routing for each celery task, like from db.Model
"""
import os

from typing import Dict, Generator

from celery import Celery
from flask import current_app

from pma_api import create_app
from pma_api.manage.db_mgmt import download_dataset
from pma_api.manage.initdb_from_wb import InitDbFromWb
from pma_api.task_utils import progress_update_callback

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


# @celery.task(bind=True)  # TO-DO: fix action_url when works
# def activate_dataset_request(self, dataset_id: str,
#                              destination_host_url: str,
#                              dataset: FileStorage = None) -> Dict:
#     """Activate dataset to be uploaded and actively used on target server.
#
#     Args:
#         self (Celery.task): Required Celery obj ref. Not to be used as param.
#         dataset_id (str): Name of dataset to send.
#         destination_host_url (str): URL of server to apply dataset.
#         dataset (FileStorage): Optional dataset object
#
#     Side effects:
#         self: Updates state.
#
#     Returns:
#         dict: Results.
#
#     TO-DO: Split upload & run db script into 2
#     """
#     action_route = 'activate_dataset'
#     # action_url: str = join_url_parts(destination_host_url, action_route)
#     action_url: str = join_url_parts('http://localhost:5000', action_route)
#     post_data: FileStorage = \
#         dataset if dataset else load_local_dataset_from_db(dataset_id)
#
#     r = requests.post(action_url, files={dataset_id: post_data})
#     state: Dict = response_to_task_state(r)
#
#     self.update_state(state=state['state'], meta=state)
#     if state['state'] in CELERY_COMPLETION_CODES:
#         return state
#
#     status_route: str = r.headers['Content-Location']
#     status_url: str = join_url_parts(destination_host_url, status_route)
#     while True:
#         r = requests.get(status_url)
#         state: Dict = response_to_task_state(r)
#         self.update_state(state=state['state'], meta=state)
#
#         if state['state'] in CELERY_COMPLETION_CODES:
#             break
#
#         time.sleep(TICK_SECONDS)
#
#     return state


@celery.task(bind=True)
def activate_dataset(self, dataset_id: str) -> Dict:
    """Activate dataset to the this server.

    Args:
        self (Celery.task): Required Celery obj ref. Not to be used as param.
        dataset_id (str): Name of dataset.

    Returns:
        dict: Results.
    """
    # TODO: 2019.03.27-jef: This shouldn't be necessary, but for some reason,
    #  even though all instances of our config have this set off, the attr
    #  doesn't even seem to appear unless it is set here.
    app.config.SQLALCHEMY_ECHO = False

    callback: Generator = \
        progress_update_callback(task_obj=self, verbose=True)

    next(callback)

    file_path: str = download_dataset(int(dataset_id))
    this_task = InitDbFromWb(
        callback=callback,
        api_file_path=file_path,
        _app=app)
    this_task.run()

    callback.close()
    return {'current': 100, 'total': 100, 'status': 'Completed'}

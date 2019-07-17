"""Tasks

# TODO: Add dynamic routing for each celery task, like from db.Model
"""
from typing import Dict, Generator, List

from celery import Celery

from pma_api.app import PmaApiFlask
from pma_api.error import PmaApiTaskDenialError
from pma_api.manage.db_mgmt import download_dataset
from pma_api.manage.initdb_from_wb import InitDbFromWb
from pma_api.task_utils import progress_update_callback
from pma_api.utils import get_app_instance

app: PmaApiFlask = get_app_instance()
celery = Celery(
    app.name,
    broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


CELERY_COMPLETION_CODES = ('FAILURE', 'SUCCESS')


# TODO 2019.04.15-jef: This feature would be ideal to add back.
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

    TODOs: 2019.03.27-jef
        1. This would be better as part of a wrapper func to all task funcs,
        until we allow for concurrent tasks.
        2. This shouldn't be necessary, but for some reason,
        even though all instances of our config have this set off, the attr
        doesn't even seem to appear unless it is set here.

    Args:
        self (Celery.task): Required Celery obj ref. Not to be used as param.
        dataset_id (str): Name of dataset.

    Returns:
        dict: Results.
    """
    from pma_api.models import Task

    active_task_ids: List[str] = Task.get_present_tasks()  # TO-DO 1
    if active_task_ids:
        raise PmaApiTaskDenialError

    app.config.SQLALCHEMY_ECHO = False  # TO-DO 2
    callback: Generator = \
        progress_update_callback(task_obj=self, verbose=True)
    task_id: str = self.request.id

    try:
        Task.register_active(task_id)
        next(callback)  # readies callback to start receiving task updates

        file_path: str = download_dataset(int(dataset_id))

        this_task = InitDbFromWb(
            callback=callback,
            api_file_path=file_path,
            _app=app)
        this_task.run()
        return {'current': 100, 'total': 100, 'status': 'Completed'}
    finally:
        callback.close()
        Task.register_inactive(task_id)

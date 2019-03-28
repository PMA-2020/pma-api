"""Administration related routes"""
import os
from typing import List, Dict, Union

from celery.exceptions import NotRegistered
from celery.result import AsyncResult
from flask import jsonify, request, render_template, send_file, url_for, \
    flash, redirect
from flask_user import login_required
from werkzeug.datastructures import ImmutableDict
from werkzeug.utils import secure_filename

from pma_api.config import PACKAGE_DIR_NAME
from pma_api.error import ExistingDatasetError
from pma_api.routes import root


@root.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_route():
    """Route to admin portal for uploading and managing datasets.

    .. :quickref: admin; Route to admin portal for uploading and managing
    datasets.

    For more information on the features that will be added to this route,
        take a look at: https://github.com/PMA-2020/pma-api/issues/32

    # GET REQUESTS
    Args: n/a

    Query Args: n/a

    Returns:
        flask.render_template(): A rendered HTML template.

    Examples: n/a

    # POST REQUESTS
    Receives a file uploaded, which is of the type:
    ImmutableMultiDict([('file', <FileStorage: 'FILENAME' ('FILETYPE')>)])
    """
    from pma_api.manage.db_mgmt import list_cloud_datasets, download_dataset, \
        delete_dataset
    from pma_api.task_utils import upload_dataset

    # upload
    if request.method == 'POST':
        try:
            file = request.files['file']
            filename = secure_filename(file.filename)
            file_url: str = upload_dataset(filename=filename, file=file)
            return jsonify({'success': bool(file_url)})
        except ExistingDatasetError as err:
            return jsonify({'success': False, 'message': str(err)})
        except Exception as err:
            msg = 'An unexpected error occurred.\n' + \
                  err.__class__.__name__ + ': ' + str(err)
            return jsonify({'success': False, 'message': msg})

    elif request.method == 'GET':
        if request.args:
            args = request.args.to_dict()

            if 'download' in args:
                # TODO: Delete tempfile after sending
                tempfile_path: str = download_dataset(
                    version_number=int(args['download']))
                return send_file(
                    filename_or_fp=tempfile_path,
                    attachment_filename=os.path.basename(tempfile_path),
                    as_attachment=True)

            if 'delete' in args:
                try:
                    delete_dataset(version_number=int(args['delete']))
                except FileNotFoundError as err:
                    msg = 'FileNotFoundError: ' + str(err)
                    # Uses Bootstrap 4.0 alert categories:
                    # https://getbootstrap.com/docs/4.0/components/alerts/
                    flash(message=msg, category='danger')
                return redirect(url_for('root.admin_route'))

            activation_args = ('activate', 'applyStaging', 'applyProduction')
            if any(x in args for x in activation_args):
                from pma_api.tasks import activate_dataset

                dataset_name, server_url = '', ''
                if 'activate' in args:
                    # TODO: If already active, return 'already active!'
                    # Should be doing this in the client anyway.
                    dataset_name = args['activate']
                    activate_dataset(dataset_id=dataset_name)
                else:
                    if 'applyStaging' in args:
                        dataset_name = args['applyStaging']
                        server_url = os.getenv('STAGING_URL')
                    elif 'applyProduction' in args:
                        dataset_name = args['applyProduction']
                        server_url = os.getenv('PRODUCTION_URL')
                    activate_dataset(dataset_id=dataset_name,
                                     destination_host_url=server_url)

        datasets: List[Dict[str, str]] = list_cloud_datasets()
        this_env = os.getenv('ENV_NAME', 'development')

        return render_template('admin.html',
                               datasets=datasets,
                               this_env=this_env)


# @root.route('/activate_dataset_request', methods=['POST'])
# @login_required
# def activate_dataset_request() -> jsonify:
#     """Activate dataset to be uploaded and actively used on target server.
#
#     Params:
#         dataset_name (str): Name of dataset to send.
#         destination_host_url (str): URL of server to apply dataset.
#
#     Returns:
#         json.jsonify: Results.
#     """
#     from pma_api.tasks import activate_dataset_request
#
#     dataset_id: str = request.form['datasetID']
#     destination_env: str = request.form['destinationEnv']
#     # destination: str = \
#     #     os.getenv('PRODUCTION_URL') \
#     #         if destination_env == 'production' else \
#     #     os.getenv('STAGING_URL') \
#     #         if destination_env == 'staging' else \
#     #         LOCAL_DEVELOPMENT_URL
#
#     # TODO: upload dataset if needed
#     dataset_needed = False
#     dataset: FileStorage = None if dataset_needed else None
#     #
#
#     # TODO - yield: init_wb, celery tasks and routes
#     task = activate_dataset_request.apply_async(kwargs={
#         'dataset_id': dataset_id,
#         # 'destination_host_url': destination,
#         'dataset': dataset})
#
#     response_data = jsonify({})
#     response_http_code = 202  # Accepted
#     response_headers = \
#         {'Content-Location': url_for('root.taskstatus', task_id=task.id)}
#
#     return response_data, response_http_code, response_headers


# @login_required  # Transfer creds from sending to receiving server?
@root.route('/activate_dataset', methods=['POST'])
def activate_dataset() -> jsonify:
    """Activate dataset to the this server.

    Params:
        dataset_name (str): Name of dataset.

    Returns:
        json.jsonify: Results.
    """
    from time import sleep
    from pma_api.tasks import activate_dataset as activate

    form: ImmutableDict = request.form
    python_var, js_var = 'datasetID', 'dataset_ID'
    dataset_id: str = form[js_var] if js_var in form else form[python_var]

    # # to-do 2019-04-02 jef: delete this; dont think needed anymore
    # from pma_api.task_utils import upload_dataset
    # files: ImmutableDict = request.files
    # if files:
    #     filenames = list(files.keys())
    #     if len(filenames) > 1:
    #         msg = 'Only one dataset may be activated at a time.'
    #         raise PmaApiException(msg)
    #     dataset_id: str = filenames[0]
    #     dataset: FileStorage = files[dataset_id]
    #     dataset_name = 'to-do'
    #     try:
    #         upload_dataset(filename=dataset_name, file=dataset)
    #     except ExistingDatasetError:
    #         pass  # Ignoring this; non-issue

    # TODO 2019.04.03-jef: No idea why sometimes fails to start
    i, retries, successfully_started, taskid, sleep_secs = 0, 5, False, '', 1
    while i < 5 and not successfully_started:
        task: AsyncResult = \
            activate.apply_async(kwargs={'dataset_id': dataset_id})
        successfully_started = task.state not in ('FAILURE', 'SUCCESS')
        if not successfully_started:
            sleep(sleep_secs)
        else:
            taskid: str = task.id

    response_data = jsonify({})
    response_http_code = 202  # Accepted
    response_headers = \
        {'Content-Location': url_for('root.taskstatus', task_id=taskid)}

    return response_data, response_http_code, response_headers


# @login_required
# Resulting in error:
# File "flask_user/user_mixin.py", line 52, in get_user_by_token
#  user_password = '' if user_manager.USER_ENABLE_AUTH0 else user.password[-8:]
# AttributeError: 'NoneType' object has no attribute 'password'
@root.route('/status/<task_id>', methods=['GET'])
def taskstatus(task_id: str) -> jsonify:
    """Get task status

    Args:
        task_id (str): ID with which to look up task in task queue

    Returns:
        jsonify: Response object
    """
    from pma_api.tasks import celery

    err = 'Unexpected error occurred while processing task.'
    task: Union[AsyncResult, NotRegistered] = \
        celery.AsyncResult(task_id)
    state: str = task.state

    # TODO
    # noinspection PyTypeChecker
    info: Union[Dict, NotRegistered] = task.info
    info_available: bool = \
        info is not None and not isinstance(info, NotRegistered)

    # TODO: temp: why errors detected?
    # noinspection PyUnusedLocal
    error_detected: bool = \
        info is not None and hasattr(info, 'args') \
        and info.args \
        and ('Error' in info.args[0] or 'error' in info.args[0])

    if state == 'FAILURE':
        # to-do: I know I can receive tuple when fail, but not sure what type
        # 'task' is in that case
        # noinspection PyUnresolvedReferences
        info: tuple = task.info.args
        status: str = '' if not info \
            else info[0] if isinstance(info, tuple) and len(info) == 1 \
            else str(list(info))

        # TODO: task.result = 'pma_api.tasks.activate_dataset'; why?
        status: str = \
            status if not status.startswith(PACKAGE_DIR_NAME) else err

        static_report: Dict[str, Union[str, int]] = {
            'id': task_id,
            'url': request.url,
            'state': state,
            'status': status,
            'current': 0,
            'total': 1,
            'result': state}  # to-do: remove all instances of 'result'?}
        dynamic_report = {}
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
            info['total']if info_available and 'total' in info else 1
        static_report: Dict[str, Union[str, int, float]] = {
            'id': task_id,
            'url': request.url,
            'state': state,
            'status': status,
            'current': current,
            'total': total}
        dynamic_report: Dict = {} \
            if not task.info \
            or not isinstance(task.info, dict) \
            or task.info == {} \
            or 'args' not in task.info.keys() \
            or not task.info['args'] \
            else task.info['args']

    report: Dict[str, Union[str, int, float]] = {
        **static_report,
        **dynamic_report}

    return jsonify(report)


# TODO: testing
@root.route('/longtask', methods=['POST'])
@login_required
def longtask():
    """Long task"""
    from pma_api.tasks import long_task
    task = long_task.apply_async()

    response_data = jsonify({})
    response_http_code = 202  # Accepted
    response_headers = \
        {'Content-Location': url_for('root.taskstatus', task_id=task.id)}

    return response_data, response_http_code, response_headers

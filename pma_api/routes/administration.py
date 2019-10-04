"""Administration related routes"""
import json
import os
import re
from typing import Dict, Union, List

from botocore.exceptions import EndpointConnectionError
from flask import jsonify, request, render_template, send_file, url_for, \
    flash, redirect, Response
from flask_user import login_required
from werkzeug.datastructures import ImmutableDict
from werkzeug.utils import secure_filename

from pma_api.error import ExistingDatasetError, PmaApiTaskDenialError, \
    MalformedApiDatasetError
from pma_api.routes import root


@root.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_route():
    """Route to admin portal for uploading and managing datasets.

    .. :quickref: admin; Route to admin portal for uploading and managing
    datasets.

    Notes:
        - flash() uses Bootstrap 4.0 alert categories,
        https://getbootstrap.com/docs/4.0/components/alerts/

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
    from pma_api.models import ApiMetadata, Task
    from pma_api.task_utils import upload_dataset

    # upload
    if request.method == 'POST':
        try:
            file = request.files['file']
            filename = secure_filename(file.filename)
            file_url: str = upload_dataset(filename=filename, file=file)
            return jsonify({'success': bool(file_url)})
        except (MalformedApiDatasetError, ExistingDatasetError) as err:
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
                    flash(message=msg, category='danger')
                return redirect(url_for('root.admin_route'))

        active_api_dataset: Dict = \
            ApiMetadata.get_current_api_data(as_json=True)
        # TODO 2019.04.18-jef: active_dataset_version seems messy / breakable
        active_dataset_version: str = \
            re.findall(r'-v[0-9]*', active_api_dataset['name'])[0]\
            .replace('-v', '')

        present_task_list: List[str] = Task.get_present_tasks()
        task_id_url_map: Dict[str, str] = {
            task_id: url_for('root.taskstatus', task_id=task_id)
            for task_id in present_task_list}
        present_tasks: str = json.dumps(task_id_url_map)

        try:
            datasets: List[Dict[str, str]] = list_cloud_datasets()
        except EndpointConnectionError:
            msg = 'Connection Error: Unable to connect to data storage ' \
                'server to retrieve list of datasets.'
            datasets: List[Dict[str, str]] = []
            flash(message=msg, category='danger')

        return render_template(
            'admin.html',
            datasets=datasets,  # List[Dict[str, str]]
            active_dataset_version=active_dataset_version,  # int
            active_tasks=present_tasks,  # str(json({id: url}))
            this_env=os.getenv('ENV_NAME', 'development'))  # str


# @login_required  # Transfer creds from sending to receiving server?
@root.route('/activate_dataset', methods=['POST'])
def activate_dataset() -> jsonify:
    """Activate dataset to the this server.

    Params:
        dataset_name (str): Name of dataset.

    Returns:
        json.jsonify: Results.
    """
    from pma_api.tasks import activate_dataset as activate
    from pma_api.task_utils import start_task

    try:
        form: ImmutableDict = request.form  # Browser request
        if not form:
            form: Dict = request.get_json(force=True)  # CLI request
        python_var, js_var = 'datasetID', 'dataset_ID'
        dataset_id: str = form[js_var] if js_var in form else form[python_var]

        task_id: str = \
            start_task(func=activate, kwarg_dict={'dataset_id': dataset_id})
        host_url: str = request.host_url  # localhost, pma-api.pma2020.org, etc
        host_url: str = host_url[:-1]  # remove trailing / character
        url_path: str = url_for('root.taskstatus', task_id=task_id)  # /status
        url: str = host_url + url_path

        response_http_code: int = 202  # Accepted
        response_data: Response = jsonify({})
        response_headers: Dict[str, str] = {'Content-Location': url}
    except PmaApiTaskDenialError as err:
        response_http_code: int = 403  # Forbidden
        response_data: Response = jsonify({})
        response_headers: Dict[str, str] = {'detail': str(err)}

    return response_data, response_http_code, response_headers


# @login_required
# Resulting in error:
# File "flask_user/user_mixin.py", line 52, in get_user_by_token
#  user_password = '' if user_manager.USER_ENABLE_AUTH0 else user.password[-8:]
# AttributeError: 'NoneType' object has no attribute 'password'
@root.route('/status/<task_id>', methods=['GET'])
def taskstatus(task_id: str) -> jsonify:
    """Get task status

    TODOs
        1. Low priority. Get correct exception types or find some other
        way to do this better. Annoyingly, sometimes info isn't a dict, and
        sometimes doesn't have key 'args', and I think there are even more
        edge cases.

    Args:
        task_id (str): ID with which to look up task in task queue

    Returns:
        jsonify: Response object
    """
    from pma_api.task_utils import get_task_status

    report: Dict[str, Union[str, int, float]] = \
        get_task_status(task_id=task_id, return_format='dict')
    report['url']: str = request.url

    return jsonify(report)


# TODO 2019.04.15-jef: This feature would be ideal to add back. This would
#  allow the user to remotely activate dataset on another server (e.g. prod
#  from staging).
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
#     # TO-DO: upload dataset if needed
#     dataset_needed = False
#     dataset: FileStorage = None if dataset_needed else None
#     #
#
#     # TO-DO: If using this code again, use start_task() function, or make
#     #  sure to otherwise specify the correct queue
#     # TO-DO - yield: init_wb, celery tasks and routes
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

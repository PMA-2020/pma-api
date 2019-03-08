"""Unversioned routes at the root of the server."""
from io import BytesIO
import os

from flask import jsonify, request, render_template, send_file, url_for
from werkzeug.datastructures import FileStorage, ImmutableDict
from werkzeug.utils import secure_filename

from pma_api.config import LOCAL_DEVELOPMENT_URL
from pma_api.error import ExistingDatasetError, PmaApiException

from pma_api.routes import root


@root.route('/admin', methods=['GET', 'POST'])
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
    from pma_api.models import Dataset
    from pma_api.task_utils import upload
    # for uploads
    if request.method == 'POST':
        try:
            file = request.files['file']
            filename = secure_filename(file.filename)
            upload(filename=filename, file=file)
            return jsonify({'success': True})
        except ExistingDatasetError as err:
            return jsonify({'success': False, 'message': str(err)})
        except Exception as err:
            msg = 'An unexpected error occurred:\n\n' + str(err)
            return jsonify({'success': False, 'message': msg})

    elif request.method == 'GET':
        if request.args:
            args = request.args.to_dict()

            if 'download' in args:
                file_obj = Dataset.query.filter_by(
                    dataset_display_name=args['download']).first()
                return send_file(
                    filename_or_fp=BytesIO(file_obj.data),
                    attachment_filename=file_obj.dataset_display_name,
                    as_attachment=True)

            # TODO: @Joe/Richard: Apply dataset.
            elif 'applyStaging' or 'applyProduction' or 'activate' in args:
                dataset_name, server_url = '', ''
                if 'activate' in args:
                    # TODO: If already active, return 'already active!'
                    # Should be doing this in the client anyway.
                    from pma_api.tasks import activate_dataset_to_self
                    dataset_name = args['activate']
                    activate_dataset_to_self(dataset_id=dataset_name)
                else:
                    from pma_api.tasks import activate_dataset_request
                    if 'applyStaging' in args:
                        dataset_name = args['applyStaging']
                        server_url = os.getenv('STAGING_URL')
                    elif 'applyProduction' in args:
                        dataset_name = args['applyProduction']
                        server_url = os.getenv('PRODUCTION_URL')
                    activate_dataset_request(dataset_id=dataset_name,
                                             destination_host_url=server_url)

        datasets = Dataset.query.all()
        this_env = os.getenv('ENV_NAME', 'development')

        return render_template('admin.html',
                               datasets=datasets,
                               this_env=this_env)


@root.route('/activate_dataset_request', methods=['POST'])
def activate_dataset_request() -> jsonify:
    """Activate dataset to be uploaded and actively used on target server.

    Params:
        dataset_name (str): Name of dataset to send.
        destination_host_url (str): URL of server to apply dataset.

    Returns:
        json.jsonify: Results.
    """
    from pma_api.tasks import activate_dataset_request

    dataset_id: str = request.form['datasetID']
    destination_env: str = request.form['destinationEnv']
    destination: str = \
        os.getenv('PRODUCTION_URL') if destination_env == 'production' else \
        os.getenv('STAGING_URL') if destination_env == 'staging' else \
        LOCAL_DEVELOPMENT_URL

    # TODO: upload dataset if needed
    dataset_needed = False
    dataset: FileStorage = None if dataset_needed else None
    #

    # TODO - yield: init_wb, celery tasks and routes
    task = activate_dataset_request.apply_async(kwargs={
        'dataset_id': dataset_id,
        'destination_host_url': destination,
        'dataset': dataset})

    response_data = jsonify({})
    response_http_code = 202  # Accepted
    response_headers = \
        {'Content-Location': url_for('root.taskstatus', task_id=task.id)}

    return response_data, response_http_code, response_headers


@root.route('/activate_dataset', methods=['POST'])
def activate_dataset_to_self() -> jsonify:
    """Activate dataset to the this server.

    Params:
        dataset_name (str): Name of dataset.

    Returns:
        json.jsonify: Results.
    """
    from pma_api.tasks import activate_dataset_to_self
    from pma_api.task_utils import upload

    form: ImmutableDict = request.form
    files: ImmutableDict = request.files
    dataset_id: str = None

    if form:
        dataset_id: str = form['datasetName'] if 'datasetName' in form \
            else form['dataset_name']
    elif files:
        filenames = list(files.keys())
        if len(filenames) > 1:
            msg = 'Only one dataset may be activated at a time.'
            raise PmaApiException(msg)
        dataset_id: str = filenames[0]
        dataset: FileStorage = files[dataset_id]
        dataset_name = 'TODO'  # TODO

        try:
            upload(filename=dataset_name, file=dataset)
        except ExistingDatasetError:
            pass  # Ignoring this; non-issue

    task = activate_dataset_to_self.apply_async(kwargs={
        'dataset_name': dataset_id})

    response_data = jsonify({})
    response_http_code = 202  # Accepted
    response_headers = \
        {'Content-Location': url_for('root.taskstatus', task_id=task.id)}

    return response_data, response_http_code, response_headers


@root.route('/status/<task_id>', methods=['GET'])
def taskstatus(task_id: str) -> jsonify:
    """Get task status

    Args:
        task_id (str): ID with which to look up task in task queue

    Returns:
        jsonify: Response object
    """
    from pma_api.tasks import celery
    task = celery.AsyncResult(task_id)
    info, state = task.info, task.state

    if state == 'FAILURE':
        status: str = str(info) if info else ''
        return jsonify({'state': state, 'status': status, 'result': state,
                        'current': 0, 'total': 1})

    return jsonify({
        'state': state,
        'status': info['status'] if info and 'status' in info else state,
        'current': info['current'] if info and 'current' in info else 0,
        'total': info['total'] if info and 'total' in info else 1})


# TODO: testing
@root.route('/longtask', methods=['POST'])
def longtask():
    """Long task"""
    from pma_api.tasks import long_task
    task = long_task.apply_async()

    response_data = jsonify({})
    response_http_code = 202  # Accepted
    response_headers = \
        {'Content-Location': url_for('root.taskstatus', task_id=task.id)}

    return response_data, response_http_code, response_headers

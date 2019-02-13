"""Unversioned routes at the root of the server."""
from io import BytesIO
import os

from flask import jsonify, request, render_template, send_file, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from pma_api.error import ExistingDatasetError

from pma_api.routes import root


# TODO: Turn into its own route
def upload(filename: str, file):
    """Upload file into database

    Args:
        filename (str): File name.
        file: File.
    """
    from pma_api.config import temp_folder_path
    from pma_api.tasks import save_file_from_request
    from pma_api.models import Dataset, db

    file_path = os.path.join(temp_folder_path(), filename)
    save_file_from_request(file=file, file_path=file_path)

    new_dataset = Dataset(file_path)
    db.session.add(new_dataset)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ExistingDatasetError('Error: A dataset named "{}" already exists'
                                   ' in DB.'.format(filename))

    # remove temp file
    if os.path.exists(file_path):
        os.remove(file_path)


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
                    from pma_api.tasks import apply_dataset_to_self
                    dataset_name = args['activate']
                    apply_dataset_to_self(dataset_name=dataset_name)
                else:
                    from pma_api.tasks import apply_dataset_request
                    if 'applyStaging' in args:
                        dataset_name = args['applyStaging']
                        server_url = os.getenv('STAGING_URL')
                    elif 'applyProduction' in args:
                        dataset_name = args['applyProduction']
                        server_url = os.getenv('PRODUCTION_URL')
                    apply_dataset_request(dataset_name=dataset_name,
                                          destination=server_url)

        datasets = Dataset.query.all()
        this_env = os.getenv('APP_SETTINGS', 'development')

        return render_template('admin.html',
                               datasets=datasets,
                               this_env=this_env)


@root.route('/apply_dataset', methods=['POST'])
def apply_dataset_route(dataset_name: str):
    """Apply dataset"""
    from pma_api.tasks import apply_dataset_to_self

    # 1. TODO: upload dataset if needed
    pass

    # 2. TODO: apply dataset - change from self to general
    task = apply_dataset_to_self.apply_async(dataset_name=dataset_name)

    return jsonify({}), 202, {'Location': url_for('root.taskstatus',
                                                  task_id=task.id)}

    # results_list = []
    #
    # for key, val in request.files.items():
    #     result = apply_dataset_to_self(dataset_name=key, dataset=val)
    #     results_list.append(result)
    #
    # results = results_list if len(results_list) > 1 else results_list[0]
    #
    # return jsonify(results)


@root.route('/status/<task_id>')
def taskstatus(task_id):
    """Get task status"""
    from pma_api.tasks import long_task
    task = long_task.AsyncResult(task_id)

    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


# TODO: testing
@root.route('/longtask', methods=['POST'])
def longtask():
    """Long task"""
    from pma_api.tasks import long_task
    task = long_task.apply_async()

    return jsonify({}), 202, {'Location': url_for('root.taskstatus',
                                                  task_id=task.id)}

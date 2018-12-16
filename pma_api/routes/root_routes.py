"""Unversioned routes at the root of the server."""
from io import BytesIO
import os

from flask import Blueprint, jsonify, redirect, request, render_template, \
    send_file
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

root = Blueprint('root', __name__)

from pma_api.error import ExistingDatasetError


@root.route('/')
def root_route():
    """Root route.

    .. :quickref: Root; Redirects to resources list or documentation depending
     on MIME type

    Args:
        n/a

    Returns:
        func: get_resources() if 'application/json'
        func: redirect() to docs if 'text/html'

    Details:
        Redirects implicitly if MIME type does not explicitly match what is
        expected.
    """
    request_headers = request.accept_mimetypes\
        .best_match(['application/json', 'text/html'])

    if request_headers == 'text/html':
        return redirect('http://api-docs.pma2020.org', code=302)
    else:
        from .endpoints.api_1_0.collection import get_resources as res
        return res() if request_headers == 'application/json' else res()


@root.route('/docs')
def documentation():
    """Documentation.

    .. :quickref: Docs; Redirects to official documentation.

    Args:
        n/a

    Returns:
        redirect(): Redirects to official documentation.
    """
    return redirect('http://api-docs.pma2020.org', code=302)


@root.route('/version')
def show_version():
    """Show API version data.

    .. :quickref: Version; API versioning data.

    Args:
        n/a

    Returns:
        String: Version number.

    Details:
        Displays API's 2-part semantic version number. ALso displays versioning
        for datasets used.

    Example:
        .. code-block:: json
           :caption: GET /v1/version
           :name: example-of-endpoint-version

            {
              "datasetMetadata": [
                {
                  "createdOn": "Fri, 13 Jul 2018 20:25:42 GMT",
                  "hash": "339ce036bdee399d449f95a1d4b3bb8f",
                  "name": "api_data-2018.03.19-v29-SAS",
                  "type": "api"
                },
                {
                  "createdOn": "Fri, 13 Jul 2018 20:25:43 GMT",
                  "hash": "469542a93241da0af80269b6d7352600",
                  "name": "ui_data-2017.10.02-v4-jef",
                  "type": "ui"
                }
              ],
              "version": "0.1.9"
            }
    """
    from pma_api.response import QuerySetApiResult
    return jsonify(QuerySetApiResult.metadata())


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
        from pma_api.tasks import apply_dataset_request
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
            elif 'applyStaging' or 'applyProduction' in args:
                dataset_name, server_url = '', ''
                if 'applyStaging' in args:
                    dataset_name = args['applyStaging']
                    server_url = os.getenv('STAGING_URL')
                elif 'applyProduction' in args:
                    dataset_name = args['applyProduction']
                    server_url = os.getenv('PRODUCTION_URL')
                apply_dataset_request(dataset_name=dataset_name,
                                      destination=server_url)

        datasets = Dataset.query.all()

        return render_template('admin.html', datasets=datasets)


@root.route('/apply_dataset', methods=['POST'])
def apply_dataset_route():
    """Apply dataset."""
    from pma_api.tasks import apply_dataset_to_self

    results_list = []

    for key, val in request.files.items():
        result = apply_dataset_to_self(dataset_name=key, dataset=val)
        results_list.append(result)

    results = results_list if len(results_list) > 1 else results_list[0]
    return jsonify(results)

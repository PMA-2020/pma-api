"""Definition of application object."""
import os
import platform
from io import BytesIO

import requests
from celery import Celery
from flask import Blueprint, jsonify, redirect, request, render_template, \
    send_file
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from .app import PmaApiFlask
from .config import config
from .models import db
from .response import QuerySetApiResult
from .models import Dataset
from .config import basedir

root = Blueprint('root', __name__)


def temp_folder_path():
    """Get the path to temp upload folder."""
    if platform.system() == 'Windows':
        return basedir + '\\temp'
    return basedir + '/temp/'


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
        from .api_1_0.collection import get_resources as res
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
    return jsonify(QuerySetApiResult.metadata())


def create_app(config_name=os.getenv('FLASK_CONFIG', 'default')):
    """Create configured Flask application.

    Args:
        config_name (str): Name of the configuration to be used.

    Returns:
        Flask: Configured Flask application.
    """
    # noinspection PyShadowingNames
    app = PmaApiFlask(__name__)
    app.config.from_object(config[config_name])

    celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)

    CORS(app)
    db.init_app(app)
    app.register_blueprint(root)

    from .api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix='/v1')

    return app


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
    if request.method == 'POST':
        try:
            file = request.files['file']
            filename = secure_filename(file.filename)
            file_path = os.path.join(temp_folder_path(), filename)

            try:
                file.save(file_path)
            except FileNotFoundError:
                os.mkdir(temp_folder_path())
                file.save(file_path)
            new_dataset = Dataset(file_path)
            db.session.add(new_dataset)

            try:
                db.session.commit()
            except IntegrityError:
                msg = 'Error: A dataset named "{}" already exists in the ' \
                      'database'.format(filename)
                return jsonify({'success': False, 'message': msg})

            # remove temp file
            if os.path.exists(file_path):
                os.remove(file_path)

            return jsonify({'success': True})
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

            # TODO: @Joe/Richard
            elif 'applyStaging' or 'applyProduction' in args:
                arg = 'applyStaging' if 'applyStaging' in args \
                    else 'applyProduction'
                # post_url = os.getenv('STAGING_URL') if 'applyStaging' in args
                #     else os.getenv('APPLY_PRODUCTION')
                # TODO: Make /upload route. Let's test in localhost first.
                post_url = 'localhost:5000/upload'

                dataset_obj = Dataset.query.filter_by(
                    dataset_display_name=args[arg]).first()

                # Maybe we can read file like this instead of temp saving it?
                file = BytesIO(dataset_obj.data).read()
                # file = os.path.join(temp_folder_path(), args[arg])

                with open(file, 'w+b') as f:
                    try:
                        f.write(dataset_obj.data)
                    except FileNotFoundError:
                        os.mkdir(temp_folder_path())
                        f.write(dataset_obj.data)

                with open(file, 'rb') as f:
                    # noinspection PyUnusedLocal
                    r = requests.post(post_url, files={'file': f})
                # remove file from disk after sending

                # TODO
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
                return render_template('index.html',
                                       datasets=Dataset.query.all())

        else:
            return render_template('index.html', datasets=Dataset.query.all())

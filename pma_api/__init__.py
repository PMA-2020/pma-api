"""Definition of application object."""
import os
from sys import stderr

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
    1. Receives a file uploaded, which is of the type:
    ImmutableMultiDict([('file', <FileStorage: 'FILENAME' ('FILETYPE')>)])

    2. Dataset download
    TODO

    # Excepts: IntegrityError when same file is uploaded more than once.
    """
    if request.method == 'POST':
        try:
            file = request.files['file']
            filename = secure_filename(file.filename)
            upload_folder = basedir + '/temp_uploads'
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            new_dataset = Dataset(file_path)
            db.session.add(new_dataset)
            db.session.commit()

            if os.path.exists(file_path):
                os.remove(file_path)
        except IntegrityError as err:  # occurs when same file is uploaded 2x
            print(err, file=stderr)
            # TODO @Joe: For some reason, it's returning the stacktrace to the
            # user. - jef 2018/10/19

    elif request.method == 'GET':
        # request.args won't actually look like this; need to search for a
        # key called "download", and the value should be a valid ID representin
        # a row in the datasets table.
        #
        # also, the javascript still needs to be implemented to populate the
        # url query parameter with any check(ed) dataset(s).
        if request.args:
            args = request.args.to_dict()
            if 'download' in args:
                file_obj = None
                file = None
                return send_file(file)
            elif 'apply-staging' in args:
                # add status 'applying-to-staging'
                # send notification that it is in progress
                # start a job to apply
                # - get url from env
                # - implement the logic to 'apply-local' first without a button
                # perhaps an 'upload' route
                # check back every now and then
                # when finished, update the status
                return render_template('index.html',
                                       datasets=Dataset.query.all())
            elif 'apply-production' in args:
                # same as above
                return render_template('index.html',
                                       datasets=Dataset.query.all())
        else:
            return render_template('index.html', datasets=Dataset.query.all())

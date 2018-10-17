"""Definition of application object."""
import os

from flask import Blueprint, jsonify, redirect, request,render_template
from flask_cors import CORS
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


@root.route('/admin', methods = ['GET', 'POST'])
def admin_route():
    """Route to admin portal for uploading and managing datasets.

    .. :quickref: admin; Route to admin portal for uploading and managing
    datasets.

    GET REQUESTS
    Args: n/a

    Query Args: n/a

    Returns:
        flask.render_template(): A rendered HTML template.

    Examples: n/a

    POST REQUESTS
    Receives a file uploaded, which is of the type:
    ImmutableMultiDict([('file', <FileStorage: 'FILENAME' ('FILETYPE')>)])

ImmutableMultiDict([('file', <FileStorage: 'api_data-2018.03.19-v29-SAS.xlsx' ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')>)])

    Details:
        For more information on the features that will be added to this route,
        take a look at: https://github.com/PMA-2020/pma-api/issues/32
    """

    # - Temporarily here just for reference -jef, 2018/09/04
    # return QuerySetApiResult(json_obj, 'json', queryInput=query_input,
    #                          chartOptions=chart_options)
  

    # datasets = Dataset.query.all()
    # print('test')

    # from pdb import set_trace
    # set_trace()
    if request.method == 'POST':
        file = request.files['file']      
        # Method 1 - we save as a file and create new Dataset object by passing path
        filename = secure_filename(file.filename)
        upload_folder = basedir + '/temp_uploads'

        


        file.save(os.path.join(upload_folder, filename))
        # filename = secure_filename(file.filename)
        # file.save('/Users/richardnguyen5/Desktop' + filename)
        # file_path = 'I dont know yet'
        # new_dataset = Dataset(file_path=file_path)

        # Method 2 - Just create new Dataset object by passing the actual file
        new_dataset = Dataset(file_path=os.path.join(upload_folder, filename))
        # from pdb import set_trace; set_trace()

        db.session.add(new_dataset)
        db.session.commit()

    # elif request.method == 'GET':
    return render_template('index.html', datasets = Dataset.query.all())


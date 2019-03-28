"""Dynamically resource-based routing

For any model resources that do not have explicit static routes created, this
route will attempt to return a standardized list of results for that model.
"""
import os
from typing import Union, List

from flask import request
from flask_sqlalchemy import Model

from pma_api import db
from pma_api.response import QuerySetApiResult
from pma_api.config import PROJECT_ROOT_PATH, \
    SQLALCHEMY_MODEL_ATTR_QUERY_IGNORES as IGNORES
from pma_api.utils import get_db_models

from . import api


db_models: List[Model] = get_db_models(db)
# PyUnresolvedReferences: Doesn't recognize existing attr __tablename__
# noinspection PyUnresolvedReferences
resource_model_map = {
    x.__tablename__: x for x in db_models
}


def models_to_dicts(models: [Model], ignores: () = IGNORES) -> [dict]:
    """Converts list of SqlAlchemy Model objects to dictionaries

    Args:
        models (list(Model)): List of SqlAlchemy Model objects
        ignores (tuple): Attributes to not include in dict

    Returns:
        list(dict): List of dictionaries
    """
    dicts: [dict] = [
        {
            k: v
            for k, v in x.__dict__.items() if k not in ignores
        }
        for x in models
    ]

    return dicts


@api.route('/<resource>')
def dynamic_route(resource: str) -> Union[QuerySetApiResult, str]:
    """Dynamically resource-based routing

    For any model resources that do not have explicit static routes created,
    this route will attempt to return a standardized list of results for that
    model.

    Args:
        resource(str): Resource requested in url of request

    Returns:
        QuerySetApiResult: Records queried for resource
        str: Standard 404

    # TODO 1: Allow for public/non-public access settings. Psuedo code:
    # access_ok = hasattr(model, 'access') and model['access']['api'] \
    #             and model['access']['api']['public']
    # public_attrs = [x for x in model['access']['api']['attributes']
    #                 if x['public']]
    # # filter out key value pairs that are not public
    # # return json

    # TODO 5: Ideally I'd like to use a different approach, i.e. dynamically
    # generate and register a list of routes at server start.
    """

    model = resource_model_map[resource] \
        if resource in resource_model_map else None

    if model is None:
        # TODO 2: There's probably a better way to handle 404's in this case
        msg_404 = 'Error 404: Page not found' + '<br/>'
        resource_h1 = 'The resources available are limited to the following ' \
                      + '<ul>'
        resources: str = '<li>' + \
                         '</li><li>'.join(resource_model_map.keys()) + '</ul>'
        msg = '<br/>'.join([msg_404, resource_h1, resources])
        return msg

    objects: [Model] = model.query.all()

    if not request.args:
        dict_objs: [{}] = models_to_dicts(objects)
        QuerySetApiResult(record_list=dict_objs, return_format='json')

    query_dir = os.path.join(PROJECT_ROOT_PATH, 'pma_api')
    query_template_path = os.path.join(query_dir, 'python_query_template.py')
    query_tempfile_path = os.path.join(query_dir, 'python_query_tempfile.py')

    # TODO: review https://nedbatchelder.com/blog/201206/
    #  eval_really_is_dangerous.html
    arg_str = ''
    for k, v in request.args.items():
        # TODO 3: Lots of other conversions. Consider as well using the literal
        #  url string rather than request.args
        v = 'True' if v == 'true' else 'False' if v == 'false' else v
        arg_str += '_.{} == {}'.format(k, v)

    with open(query_template_path, 'r') as file:
        txt = file.read()

    # TODO 4: Use actual temp files with random names for concurrency
    with open(query_tempfile_path, 'w') as file:
        txt = txt.replace("'$'", arg_str)
        file.write(txt)
    # noinspection PyUnresolvedReferences
    from pma_api.python_query_tempfile import interpolated_query
    filtered_objs: [Model] = interpolated_query(objects)
    os.remove(query_tempfile_path)

    dict_objs: [{}] = models_to_dicts(filtered_objs)
    response = QuerySetApiResult(record_list=dict_objs, return_format='json')

    return response

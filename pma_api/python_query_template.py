"""Dynamic interpolated runtime python queries"""
from flask_sqlalchemy import Model

from pma_api.config import SQLALCHEMY_MODEL_ATTR_QUERY_IGNORES as IGNORES
from pma_api.error import PmaApiException


def interpolated_query(objects: [Model]) -> [Model]:
    """Interpolates a templated 'query' in form of list comprehension.

    Args:
        objects (list(flask_sqlalchemy.Model)): List of SqlAlchemy Models.

    Returns
        list(flask_sqlalchemy.Model): Filtered list

    Raises:
        PmaApiException: If attribute requested not found
    """
    try:
        filtered_list = [_ for _ in objects if '$']
    except AttributeError:
        model_attrs = \
            [k for k in objects[0].__dict__.keys() if k not in IGNORES]
        msg = 'An error occurred during query. Attribute requested was not ' \
              'found. The following attributes are available: \n' + \
              str(model_attrs)
        raise PmaApiException(msg)

    return filtered_list

"""Assortment of utilities for application."""
import itertools
import operator
import os
import random
from typing import List

from flask_sqlalchemy import Model, SQLAlchemy

from pma_api.app import PmaApiFlask

B64_CHAR_SET = ''.join(('abcdefghijklmnopqrstuvwxyz',
                        'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                        '0123456789-_'))
seen = {None}
random.seed(2020)


def next64():
    """Random string generator.

    Returns:
        str: Randomly generated string.
    """
    n_char = 8
    result = None

    while result in seen:
        result = ''.join(random.choice(B64_CHAR_SET) for _ in range(n_char))
    seen.add(result)

    return result


def most_common(a_list: list):
    """Get most common element in a list

    Args:
        a_list (list): Any arbitrary list

    Returns:
        any: pick the highest-count/earliest item
    """
    # get an iterable of (item, iterable) pairs
    sorted_list = sorted((x, i) for i, x in enumerate(a_list))
    groups = itertools.groupby(sorted_list, key=operator.itemgetter(0))

    def _auxfun(grp):
        """Auxiliary function to get "quality" for an item

        This function should be used in tandem with max()

        Args:
            grp (iterable): an object to returned by max() if the provided
            iterable passed to max() is empty.
        """
        item, iterable = grp
        count = 0
        min_index = len(a_list)
        for _, where in iterable:
            count += 1
            min_index = min(min_index, where)

        return count, -min_index

    return max(groups, key=_auxfun)[0]


def dict_to_pretty_json(dictionary: {}) -> '':
    """Given a dictionary, pretty print JSON str

    Args:
        dictionary (dict): dictionary

    Returns:
        str: Prettified JSON string
    """
    import json

    return json.dumps(
        dictionary,
        sort_keys=True,
        indent=4,
        separators=(',', ': '))


def join_url_parts(*args: str) -> str:
    """Join parts of a url string

    Parts of a URL string may come from different sources, so joining them
    directly together may yield too many or too few '/' delimiters.

    Args:
        *args:

    Returns:
        str: Well-formed url
    """
    base_str = '/'.join(args)

    return 'http://' + base_str.replace('http://', '').replace('//', '/')


def get_db_models(db: SQLAlchemy) -> List[Model]:
    """Get list of models from SqlAlchemy

    Args:
        db: SqlAlchemy db object

    Returns:
        list(Model): List of registered SqlAlchemy models
    """
    # noinspection PyProtectedMember
    models: List[Model] = \
        [cls for cls in db.Model._decl_class_registry.values()
         if isinstance(cls, type) and issubclass(cls, db.Model)]

    return models


# TODO 2019.03.10-jef: Get this to work
def stderr_stdout_captured(func):
    """Capture stderr and stdout

    Args:
        func: A function

    Returns:
        str, str, any: stderr output, stdout output, return of function
    """
    import sys
    from io import StringIO

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured_stderr = sys.stderr = StringIO()
    captured_stdout = sys.stdout = StringIO()

    returned_value = func()

    _err: str = captured_stderr.getvalue()
    _out: str = captured_stdout.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    return _err, _out, returned_value


def get_app_instance() -> PmaApiFlask:
    """Get reference to copy of currently running application instance

    Returns:
        PmaApiFlask: PmaApiFlask application instance.
    """
    err = 'A current running app was not able to be found.'

    try:
        from flask import current_app
        app: PmaApiFlask = current_app
        if app.__repr__() == '<LocalProxy unbound>':
            raise RuntimeError(err)
    except RuntimeError:
        from pma_api import create_app
        app: PmaApiFlask = create_app(os.getenv('ENV_NAME', 'default'))

    return app

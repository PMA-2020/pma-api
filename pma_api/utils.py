"""Assortment of utilities for application."""
import itertools
import operator
import platform
import random

from pma_api.config import PROJECT_ROOT_DIR

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


def os_appropriate_folder_path(folder_name: str) -> str:
    """Get the path string to folder path, appropriate to OS.

    Args:
        folder_name (str): Folder name.

    Returns:
        str: path
    """
    if platform.system() == 'Windows':
        return PROJECT_ROOT_DIR + '\\' + folder_name
    return PROJECT_ROOT_DIR + '/' + folder_name + '/'


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

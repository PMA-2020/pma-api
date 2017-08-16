"""Assortment of utilities for application."""
import random


random.seed(2020)


B64_CHAR_SET = ''.join(('abcdefghijklmnopqrstuvwxyz',
                        'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                        '0123456789-_'))


_SEEN = set([None])


def next64():
    """Random string generator.

    Returns:
        str: Randomly generated string.
    """
    n_char = 8
    result = None
    while result in _SEEN:
        result = ''.join(random.choice(B64_CHAR_SET) for _ in range(n_char))
    _SEEN.add(result)
    return result

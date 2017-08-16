"""Assortment of utilities for application."""
import random


random.seed(2020)


b64_char_set = ''.join(('abcdefghijklmnopqrstuvwxyz',
                        'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                        '0123456789-_'))


_seen = set([None])


def next64():
    """Random string generator.

    Returns:
        str: Randomly generated string.
    """
    n_char = 8
    result = None
    while result in _seen:
        result = ''.join(random.choice(b64_char_set) for _ in range(n_char))
    _seen.add(result)
    return result


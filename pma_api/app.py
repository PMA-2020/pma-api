"""Custom subclass for the PMA API."""
from flask import Flask, Response, jsonify


class PmaApiFlask(Flask):
    """A PMA API subclass of the Flask object."""

    def make_response(self, rv):
        """Handle custom responses: Cached vs non-cached

        Args:
            rv (Union[ApiResult, Cache, 'rv']): Model for cached or non-cached
            response, or Flask 'rv' obj as described below.

        Documentation below is taken directly from Flask.make_response.

        * * *

        :param rv: the return value from the view function. The view function
            must return a response. Returning ``None``, or the view ending
            without returning, is not allowed. The following types are allowed
            for ``view_rv``:

            ``str`` (``unicode`` in Python 2)
                A response object is created with the string encoded to UTF-8
                as the body.

            ``bytes`` (``str`` in Python 2)
                A response object is created with the bytes as the body.

            ``tuple``
                Either ``(body, status, headers)``, ``(body, status)``, or
                ``(body, headers)``, where ``body`` is any of the other types
                allowed here, ``status`` is a string or an integer, and
                ``headers`` is a dictionary or a list of ``(key, value)``
                tuples. If ``body`` is a :attr:`response_class` instance,
                ``status`` overwrites the exiting value and ``headers`` are
                extended.

            :attr:`response_class`
                The object is returned unchanged.

            other :class:`~werkzeug.wrappers.Response` class
                The object is coerced to :attr:`response_class`.

            :func:`callable`
                The function is called as a WSGI application. The result is
                used to create a response object.
        """
        from pma_api.models import Cache
        from pma_api.response import ApiResult

        if isinstance(rv, ApiResult):
            returns: jsonify = rv.to_response()
        elif isinstance(rv, Cache):
            returns = Response(rv.value, mimetype=rv.mimetype)
        else:
            returns = Flask.make_response(self, rv)

        return returns

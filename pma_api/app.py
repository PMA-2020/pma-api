"""Custom subclass for the PMA API."""
from flask import Flask, Response

from .models import Cache
from .response import ApiResult


class PmaApiFlask(Flask):
    """A PMA API subclass of the Flask object."""

    def make_response(self, rv):
        """Handle custom responses."""
        if isinstance(rv, ApiResult):
            return rv.to_response()
        elif isinstance(rv, Cache):
            return Response(rv.value, mimetype=rv.mimetype)
        return Flask.make_response(self, rv)

"""Custom subclass for the PMA API."""
from flask import Flask

from .response import QuerySetApiResult


class PmaApiFlask(Flask):
    """A PMA API subclass of the Flask object."""

    def make_response(self, rv):
        """Handle custom responses."""
        if isinstance(rv, QuerySetApiResult):
            return rv.to_response()
        return Flask.make_response(self, rv)

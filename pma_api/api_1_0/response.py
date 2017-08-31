"""Responses."""
from io import StringIO
from csv import DictWriter

from flask import Response, jsonify

from . import __version__
from ..models import WbMetadata


class QuerySetApiResult:
    """A representation of a list of records (Python dictionaries)."""

    def __init__(self, record_list, return_format, **kwargs):
        """Store the list of records and the format."""
        self.record_list = record_list
        self.return_format = return_format
        self.kwargs = kwargs

    def to_response(self):
        """Convert the list of records into a response."""
        if self.return_format == 'json':
            return self.json_response(self.record_list, **self.kwargs)
        # if _format == 'json':
        #     return json_response(data)
        # elif _format == 'csv':
        #     return csv_response(data)
        # elif _format == 'xml' or _format == 'html':
        #    return 'Format \'{}\' is not currently available.'.format(_format)
        # elif _format not in supported_formats and _format is not None:
        #     return 'Format \'{}\' is not a recognized format.'
        # else:
        #     return json_response(data)

    @staticmethod
    def json_response(record_list, **kwargs):
        """Convert a list of records into a JSON response."""
        obj = {
            **kwargs,
            'results': record_list,
            'resultSize': len(record_list),
            'metadata': QuerySetApiResult.metadata()
        }
        return jsonify(obj)

    @staticmethod
    def metadata():
        """Return metadata."""
        obj = {
            'version': __version__,
            'dataset_metadata': [item.to_json() for item in
                                 WbMetadata.query.all()]
        }
        return obj


def response(data, request_args):
    """Response."""
    if request_args == 'json' or True:
        return QuerySetApiResult(data, 'json').to_response()


def csv_response(data):
    """CSV Response."""
    string_io = StringIO()
    header = data['results'][0].keys()
    writer = DictWriter(f=string_io, fieldnames=header)
    writer.writeheader()
    writer.writerows((item for item in data['results']))
    result = string_io.getvalue()

    return Response(result, mimetype='text/csv')


def json_response(data):
    """JSON Response."""
    return jsonify(data)


# TODO: (jef/jkp 2017-08-29) Add methods for:
# * return warnings, errors
# * return version number
# * documentation
# Needs: Decision on how these should be returned.

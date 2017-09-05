"""Responses."""
from io import StringIO
from csv import DictWriter

from flask import Response, jsonify

from .__version__ import __version__


class QuerySetApiResult:
    """A representation of a list of records (Python dictionaries)."""

    def __init__(self, record_list, return_format, **kwargs):
        """Store the list of records and the format."""
        self.record_list = record_list
        self.return_format = return_format
        self.kwargs = kwargs

    def to_response(self):
        """Convert the list of records into a response."""
        if self.return_format == 'csv':
            return self.csv_response(self.record_list)
        # Default is JSON
        return self.json_response(self.record_list, **self.kwargs)

    @staticmethod
    def csv_response(record_list):
        """CSV Response."""
        # TODO (jkp 2017-09-05) Handle error (empty record_list)
        string_io = StringIO()
        header = record_list[0].keys()
        writer = DictWriter(f=string_io, fieldnames=header)
        writer.writeheader()
        writer.writerows((item for item in record_list))
        result = string_io.getvalue()
        return Response(result, mimetype='text/csv')

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
        from .models import SourceData
        obj = {
            'version': __version__,
            'dataset_metadata': [item.to_json() for item in
                                 SourceData.query.all()]
        }
        return obj


# TODO: (jef/jkp 2017-08-29) Add methods for:
# * return warnings, errors
# * return version number
# * documentation
# Needs: Decision on how these should be returned.

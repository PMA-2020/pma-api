"""Responses."""
from io import StringIO
from csv import DictWriter
from typing import List

from flask import Response, jsonify, make_response

from .__version__ import __version__


class ApiResult:
    """A representation of a generic JSON API result."""

    def __init__(self, data, metadata=None, **kwargs):
        """Store input arguments.

        Args:
            data (dict): A dictionary built up for the API to return
            metadata (dict): A dictionary of keys and values to add to the
                metadata field of the return object.
        """
        self.data = data
        self.extra_metadata = metadata
        self.kwargs = kwargs

    def to_response(self):
        """Make a response from the data."""
        metadata = self.metadata(self.extra_metadata)
        obj = {
            **self.data,
            **self.kwargs,
            'metadata': metadata
        }
        return jsonify(obj)

    @staticmethod
    def metadata(extra_metadata=None):
        """Return metadata."""
        from .models import ApiMetadata
        obj = {
            'version': __version__,
            'datasetMetadata': [item.to_json() for item in
                                ApiMetadata.query.all()]
        }
        if extra_metadata:
            obj.update(extra_metadata)
        return obj


class QuerySetApiResult(ApiResult):
    """A representation of a list of records (Python dictionaries)."""

    def __init__(self, record_list, return_format, metadata=None, **kwargs):
        """Store the list of records and the format."""
        super().__init__(record_list, metadata, **kwargs)
        self.record_list = record_list
        self.return_format = return_format

    def to_response(self):
        """Convert the list of records into a response."""
        if self.return_format == 'csv' and self.record_list:
            return self.csv_response(self.record_list)
        elif self.return_format == 'csv':  # and not self.record_list
            return make_response('', 204)
        # Default is JSON
        return self.json_response(self.record_list, self.extra_metadata,
                                  **self.kwargs)

    @staticmethod
    def csv_response(record_list):
        """CSV Response."""
        string_io = StringIO()
        header = record_list[0].keys()
        writer = DictWriter(f=string_io, fieldnames=header)
        writer.writeheader()
        writer.writerows((item for item in record_list))
        result = string_io.getvalue()
        response = Response(result, mimetype='text/csv')
        response.headers['Content-Disposition'] = \
            'attachment; filename=data.csv'
        return response

    @staticmethod
    def _remove_bytes_values(record_list: List[dict]) -> List[dict]:
        """From a list of dicts, remove any dict value that is bytes.

        Args:
            record_list(list(dict)): Records queried from db

        Returns:
            list(dict): Records with any non-JSON-serializable bytes values
            replaced with the string 'bytes'
        """
        try:
            formatted_list: [dict] = [
                {
                    k: 'bytes' if isinstance(v, bytes) else
                    v
                    for k, v in x.items()
                }
                for x in record_list
            ]

            return formatted_list

        except AttributeError:
            # record_list is not a List[dict]
            return record_list

    @staticmethod
    def json_response(record_list, extra_metadata, **kwargs):
        """Convert a list of records into a JSON response."""
        # TODO: instead of remove bytes values, convert bytes value to URL
        #  to download file
        formatted_list = QuerySetApiResult._remove_bytes_values(record_list)
        obj = {
            **kwargs,
            'results': formatted_list,
            'resultSize': len(record_list),
            'metadata': ApiResult.metadata(extra_metadata)
        }
        return jsonify(obj)


# TODO: (jef/jkp 2017-08-29) Add methods for:
# * return warnings, errors
# * return version number
# * documentation
# Needs: Decision on how these should be returned.

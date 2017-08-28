"""Responses."""
from io import StringIO
from csv import DictWriter

from flask import Response, jsonify


# TODO: Change into a class.
def response(data, request_args):
    """Response."""
    data_format = request_args.get('format', None)
    return format_response(data, data_format)


def format_response(data, _format):
    """Format response."""
    supported_formats = ('json', 'csv', 'xml', 'html')

    if _format == 'json':
        return json_response(data)
    elif _format == 'csv':
        return csv_response(data)
    elif _format == 'xml' or _format == 'html':
        return 'Format \'{}\' is not currently available.'.format(_format)
    elif _format not in supported_formats and _format is not None:
        return 'Format \'{}\' is not a recognized format.'
    else:
        return json_response(data)


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


# TODO: Add methods for:
# * return warnings, errors
# * return version number
# * documentation

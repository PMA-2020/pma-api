"""Routes related to the datalab."""
from flask import jsonify, request

from . import api
from ..response import QuerySetApiResult
from ..queries import DatalabData


@api.route('/datalab/data')
def get_datalab_data():
    """Get the correct slice of datalab data."""
    survey = request.args.get('survey', None)
    indicator = request.args.get('indicator', None)
    char_grp = request.args.get('characteristicGroup', None)
    over_time = request.args.get('overTime', 'false')
    over_time = True if over_time.lower() == 'true' else False
    json_obj = DatalabData.series_query(survey, indicator, char_grp, over_time)
    response_format = request.args.get('format', None)
    return QuerySetApiResult(json_obj, response_format)


@api.route('/datalab/combos')
def get_datalab_combos():
    """Get datalab combos."""
    survey_list = request.args.get('survey', None)
    indicator = request.args.get('indicator', None)
    char_grp = request.args.get('characteristicGroup', None)
    if survey_list:
        json_obj = DatalabData.combos_survey_list(survey_list)
        return jsonify(json_obj)
    elif indicator and char_grp:
        json_obj = DatalabData.combos_indicator_char_grp(indicator, char_grp)
        return jsonify(json_obj)
    elif indicator and not char_grp:
        json_obj = DatalabData.combos_indicator(indicator)
        return jsonify(json_obj)
    elif not indicator and char_grp:
        json_obj = DatalabData.combos_char_grp(char_grp)
        return jsonify(json_obj)
    msg = 'All request arguments supplied were empty, or none were ' \
          'supplied. Please supply all required query parameters for ' \
          'endpoint \'{endpoint}\': {params}'\
        .format(endpoint='/datalab/combos',
                params=str(['survey', 'indicator', 'characteristicGroup']))
    return jsonify({'error': msg}), 400


@api.route('/datalab/init')
def get_datalab_init():
    """Get datalab combos."""
    data = DatalabData.datalab_init()
    return jsonify(data)

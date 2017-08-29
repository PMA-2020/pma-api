"""Routes related to the datalab."""
from flask import jsonify, request

from . import api
from .response import QuerySetApiResult, response
from ..queries import DatalabData


@api.route('/datalab/data')
def get_datalab_data():
    """Get the correct slice of datalab data."""
    survey = request.args.get('survey', None)
    indicator = request.args.get('indicator', None)
    char_grp = request.args.get('characteristicGroup', None)
    json_obj = DatalabData.filter_minimal(survey, indicator, char_grp)
    return QuerySetApiResult(json_obj, 'json').to_response()


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
    # else: survey_list, indicator, char_grp are all None
    # TODO (jkp 2017-08-29) put in informative error code. Need: more time
    return 'Request args are all empty', 400


@api.route('/datalab/init')
def get_datalab_init():
    """Get datalab combos."""
    return response(data=DatalabData.datalab_init(), request_args=request.args)

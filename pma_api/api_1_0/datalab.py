"""Routes related to the datalab."""
from flask import request

from . import api
from . import caching
from ..models import Cache
from ..response import ApiResult, QuerySetApiResult
from ..queries import DatalabData


DEFAULT_PRECISION = 1


@api.route('/datalab/data')
def get_datalab_data():
    """Get the correct slice of datalab data."""
    survey = request.args.get('survey', None)
    indicator = request.args.get('indicator', None)
    char_grp = request.args.get('characteristicGroup', None)
    over_time = request.args.get('overTime', 'false')
    over_time = True if over_time.lower() == 'true' else False
    json_list = DatalabData.filter_minimal(survey, indicator, char_grp,
                                           over_time)
    precisions = list(x['precision'] for x in json_list if x['precision'] is
                      not None)
    min_precision = min(precisions) if precisions else DEFAULT_PRECISION
    for item in json_list:
        item['value'] = round(item['value'], min_precision)
    response_format = request.args.get('format', None)
    if response_format == 'csv':
        return QuerySetApiResult(json_list, response_format)
    if over_time:
        json_obj = DatalabData.data_to_time_series(json_list)
    else:
        json_obj = DatalabData.data_to_series(json_list)
    query_input = DatalabData.query_input(survey, indicator, char_grp)
    chart_options = {'precision': min_precision}
    return QuerySetApiResult(json_obj, 'json', queryInput=query_input,
                             chartOptions=chart_options)


@api.route('/datalab/combos')
def get_datalab_combos():
    """Get datalab combos."""
    survey_s = request.args.get('survey', '')
    survey_list = sorted(survey_s.split(',')) if survey_s else []
    indicator_s = request.args.get('indicator', '')
    indicator = indicator_s if indicator_s else None
    char_grp_s = request.args.get('characteristicGroup', '')
    char_grp = char_grp_s if char_grp_s else None
    json_obj = DatalabData.combos_all(survey_list, indicator, char_grp)
    request_params = request.args.to_dict()
    metadata = {'queryParameters': request_params}
    return ApiResult(json_obj, metadata=metadata)


@api.route('/datalab/init')
def get_datalab_init():
    """Get datalab combos."""
    cached = Cache.get(caching.KEY_DATALAB_INIT)
    if cached and not request.args.get('cached') == 'false':
        return cached
    json_obj = DatalabData.datalab_init()
    return ApiResult(json_obj)

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
    """Datalab client endpoint for querying data.

    .. :quickref: Datalab; Datalab client specific endpoint for querying data.

    Returns:
        json: Queried data.
    """
    survey = request.args.get('survey', None)
    indicator = request.args.get('indicator', None)
    char_grp = request.args.get('characteristicGroup', None)
    over_time = request.args.get('overTime', 'false')
    over_time = True if over_time.lower() == 'true' else False
    response_format = request.args.get('format', None)
    if response_format == 'csv':
        lang = request.args.get('lang')
        json_list = DatalabData.filter_readable(survey, indicator, char_grp,
                                                lang)
        return QuerySetApiResult(json_list, response_format)
    json_list = DatalabData.filter_minimal(survey, indicator, char_grp,
                                           over_time)
    precisions = list(x['precision'] for x in json_list if x['precision'] is
                      not None)
    min_precision = min(precisions) if precisions else DEFAULT_PRECISION
    for item in json_list:
        item['value'] = round(item['value'], min_precision)
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
    """Datalab client endpoint for querying validmetadata combinations.

    .. :quickref: Datalab; Datalab client specific endpoint for querying valid
     metadata combinations.

    The structural metadata for Datalab are:
      - Country survey rounds
      - Indicators
      - Characteristics for data disaggregation

    A valid structural metadata combination is a combination for which data
     exists. That is to say that when these metadata are used together as query
     parameters on the 'datalab/data' endpoint, actual data will be returned
     rather than nothing at all.

    Returns:
        json: List of valid metadata combinations.
    """
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
    """Datalab client endpoint for app initialization.

    .. :quickref: Datalab; Datalab client specific endpoint for app
     initialization.

    Returns:
        json: All of the necessary elements to render initial view of Datalab.
    """
    cached = Cache.get(caching.KEY_DATALAB_INIT)
    if cached and not request.args.get('cached') == 'false':
        return cached
    json_obj = DatalabData.datalab_init()
    return ApiResult(json_obj)

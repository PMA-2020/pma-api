"""Routes related to the datalab."""
from flask import request

from pma_api.config import REFERENCES
from . import api
from pma_api.models import Cache
from pma_api.response import ApiResult, QuerySetApiResult
from pma_api.queries import DatalabData


DEFAULT_PRECISION = 1


@api.route('/datalab/data')
def get_datalab_data():
    """Datalab client endpoint for querying data.

    .. :quickref: Datalab; Datalab client specific endpoint for querying data.

    Args:
        Non-REST, Python API for function has no arguments.

    Query Args:
        survey (string | list): The country survey round(s). If more than one,
        this query parameter is comma delimited with no enclosing brackets, as
        shown in example. Not required.
        indicator: (string): A single indicator.  Not required.
        characteristicGroup (string): A single characteristic group. Not
        required.
        overTime (bool): If "true", this endpoint looks for data to be plotted
        or disaggregated over a time dimension. If "false", the data is only
        disaggregated by the characteristic group. Default value for this query
        argument if left out is "false". Not required.
        format (string): Only accepts the string "csv". This will return a CSV
        file. Not required.
        lang (string): Accepts 2 letter language code, e.g. "EN" for English,
        or "FR" for French. This is used in tandem with "format=csv". Default
        value is "EN". Not required.

    Returns:
        json: Queried data.

    Details:
        Returns lists of all specific, key resources (surveys, indicators, and
        characteristics), all of which have at least one stored data point
        associated. In addition to "results" and "metadata" object, which are
        common to other endpoints, this endpoint also returns a "queryInput"
        object, which provides additional attributes for all of the query
        parameters which were passed in the request.

        While no parameters are technically required, it is expected that some
        be provided. For the Datalab client use case, all query parameters are
        typically used. The historical function of this endpoint is for the
        purpose of data visualization.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/datalab/data?survey=PMA2014_BFR1,PMA2015_BFR2&indicator=cp_mar&characteristicGroup=parity&overTime=false
           :name: example-of-collection-datalab-data

            {
              "chartOptions": {
                "precision": 1
              },
              "metadata": {
                "datasetMetadata": [
                  {
                    "createdOn": "Fri, 13 Jul 2018 20:25:42 GMT",
                    "hash": "339ce036bdee399d449f95a1d4b3bb8f",
                    "name": "api_data-2018.03.19-v29-SAS",
                    "type": "api"
                  },
                  {
                    "createdOn": "Fri, 13 Jul 2018 20:25:43 GMT",
                    "hash": "469542a93241da0af80269b6d7352600",
                    "name": "ui_data-2017.10.02-v4-jef",
                    "type": "ui"
                  }
                ],
                "version": "0.1.9"
              },
              "queryInput": {
                "characteristicGroups": [
                  {
                    "definition.id": "PAphCZZd",
                    "id": "parity",
                    "label.id": "IArHyBju"
                  }
                ],
                "indicators": [
                  {
                    "definition.id": "E6R-TrTt",
                    "id": "cp_mar",
                    "label.id": "rniE-48x",
                    "type": "indicator"
                  }
                ],
                "surveys": [
                  {
                    "country.label.id": "cizmJ6Gv",
                    "geography.label.id": "w748V1ul",
                    "id": "PMA2014_BFR1",
                    "label.id": "QY-mwT2K",
                    "partner.label.id": "YlzQ41YY"
                  },
                  {
                    "country.label.id": "cizmJ6Gv",
                    "geography.label.id": "w748V1ul",
                    "id": "PMA2015_BFR2",
                    "label.id": "RQ1bUBVJ",
                    "partner.label.id": "YlzQ41YY"
                  }
                ]
              },
              "resultSize": 2,
              "results": [
                {
                  "country.id": "BF",
                  "country.label.id": "cizmJ6Gv",
                  "geography.id": "bf_national",
                  "geography.label.id": "w748V1ul",
                  "survey.id": "PMA2014_BFR1",
                  "survey.label.id": "QY-mwT2K",
                  "values": [
                    {
                      "characteristic.id": "0-1_children",
                      "characteristic.label.id": "4CoX8mVz",
                      "value": 14.7
                    },
                    {
                      "characteristic.id": "2-3_children",
                      "characteristic.label.id": "XEcza0o1",
                      "value": 19.8
                    },
                    {
                      "characteristic.id": "4_children",
                      "characteristic.label.id": "FaUxMgNn",
                      "value": 18.8
                    }
                  ]
                },
                {
                  "country.id": "BF",
                  "country.label.id": "cizmJ6Gv",
                  "geography.id": "bf_national",
                  "geography.label.id": "w748V1ul",
                  "survey.id": "PMA2015_BFR2",
                  "survey.label.id": "RQ1bUBVJ",
                  "values": [
                    {
                      "characteristic.id": "0-1_children",
                      "characteristic.label.id": "4CoX8mVz",
                      "value": 16.8
                    },
                    {
                      "characteristic.id": "2-3_children",
                      "characteristic.label.id": "XEcza0o1",
                      "value": 25.6
                    },
                    {
                      "characteristic.id": "4_children",
                      "characteristic.label.id": "FaUxMgNn",
                      "value": 19.9
                    }
                  ]
                }
              ]
            }
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

    Args:
        Non-REST, Python API for function has no arguments.

    Query Args:
        survey (string | list): The country survey round(s). If more than one,
        this query parameter is comma delimited with no enclosing brackets, as
        shown in example. Not required.
        indicator: (string): A single indicator. Not required.
        characteristicGroup (string): A single characteristic group. Not
        required.

    Returns:
        json: List of valid metadata combinations.

    Details:
        The structural metadata for Datalab are...

        - Country survey rounds
        - Indicators
        - Characteristics for data disaggregation

        A valid structural metadata combination is a combination for which data
        exists. That is to say that when these metadata are used together as
        query parameters on the 'datalab/data' endpoint, actual data will be
        returned rather than nothing at all. While none of the query arguments
        are marked as required, a normal use case uses 1 or 2 of the three
        parameters available to this endpoint. For 0 or 3 of the
        afforementioned parameters, the "/datalab/init" and "/datalab/data"
        endpoints should typically be used respectively.

    Examples:
        **1) /v1/datalab/combos?survey=<surveys>**
        Query by survey. Get a list of indicator and characteristic
        combinations which have one or more stored data point associated with
        any of the provided surveys. From this list provided, the client
        application should have enough information to filter valid data is
        aggregated further by specified indicator(s) and characteristic(s),
        without the need for any further API calls.

        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/datalab/combos?survey=PMA2013_GHR1,PMA2014_GHR2&
           :name: example-of-collection-datalab-combos-2

            {
              "characteristicGroup.id": [
                "age_5yr_int",
                "beds",
                "edu_GH",
                "..."
              ],
              "indicator.id": [
                "IUD_all",
                "IUD_mar",
                "condom_all",
                "..."
              ],
              "metadata": {
                "datasetMetadata": [
                  "..."
                ],
                "queryParameters": {
                  "survey": "PMA2013_GHR1,PMA2014_GHR2"
                },
                "version": "0.1.9"
              },
              "survey.id": [
                "PMA2013_CDR1_Kinshasa",
                "PMA2013_GHR1",
                "PMA2014_BFR1",
                "..."
              ]
            }

        **2) /v1/datalab?indicator=<id>**
        Query by indicator. In this example, "Current use of any modern
        contraceptive method (all women)"

        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/datalab/combos?indicator=mcp_all
           :name: example-of-collection-datalab-combos-2

            {
              "characteristicGroup.id": [
                "age_5yr_int",
                "edu_BF",
                "edu_CD",
                "..."
              ],
              "indicator.id": [
                "IUD_all",
                "IUD_mar",
                "condom_all",
                "..."
              ],
              "metadata": {
                "datasetMetadata": [
                  "..."
                ],
                "queryParameters": {
                  "indicator": "mcp_all"
                },
                "version": "0.1.9"
              },
              "survey.id": [
                "PMA2013_CDR1_Kinshasa",
                "PMA2013_GHR1",
                "PMA2014_BFR1",
                "..."
              ]
            }

        **3) /v1/datalab?characteristicGroup=<id>**
        Query by characteristic group. In this example, "wealth quintile".

        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/datalab/combos?characteristicGroup=wealth_quintile
           :name: example-of-collection-datalab-combos-3

            {
              "characteristicGroup.id": [
                "age_5yr_int",
                "beds",
                "edu_BF",
                "..."
              ],
              "indicator.id": [
                "IUD_all",
                "IUD_mar",
                "condom_all",
                "..."
              ],
              "metadata": {
                "datasetMetadata": [
                  "..."
                ],
                "queryParameters": {
                  "characteristicGroup": "wealth_quintile"
                },
                "version": "0.1.9"
              },
              "survey.id": [
                "PMA2013_CDR1_Kinshasa",
                "PMA2013_GHR1",
                "PMA2014_CDR2_Kinshasa",
                "..."
              ]
            }

        **4) /v1/datalab/combos?<resource_1>=<id>&<resource_2>=<id>**
        Query by 2 of 3 key resources, survey being "Ghana 2013 survey round 1"
        , and indicator being "current use of any contraceptive method (all
        women)".

        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/datalab/combos?survey=PMA2013_GHR1&indicator=mcp_all
           :name: example-of-collection-datalab-combos-1

            {
              "characteristicGroup.id": [
                "age_5yr_int",
                "edu_GH",
                "marital_status",
                "..."
              ],
              "indicator.id": [
                "IUD_all",
                "IUD_mar",
                "condom_all",
                "..."
              ],
              "metadata": {
                "datasetMetadata": [
                  "..."
                ],
                "queryParameters": {
                  "indicator": "mcp_all",
                  "survey": "PMA2013_GHR1"
                },
                "version": "0.1.9"
              },
              "survey.id": [
                "PMA2013_CDR1_Kinshasa",
                "PMA2013_GHR1",
                "PMA2014_BFR1",
                "..."
              ]
            }
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


# TODO: We might as well move this cache behavior into the Flask app to apply
# it on all routes, or we could also create a new function wrapper for all
# our routese that we want to cahce.
@api.route('/datalab/init')
def get_datalab_init(cached: bool = True):
    """Datalab client endpoint for app initialization, minified.

    .. :quickref: Datalab; Datalab client specific endpoint for app
     initialization.

    Args:
        cached (bool): Return cached value? This argument is used when
        calling this function in Python, as opposed to over HTTP. If calling
        this function/route over HTTP, use the 'cached' query parameter.

    Query Args:
        None

    Returns:
        json: All of the necessary elements to render initial view of Datalab.

    Details:
        Datalab client endpoint for app initialization, minified.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/datalab/init
           :name: example-of-collection-datalab-init

            {"A significant of minified data is returned."}
    """
    cache_arg = request.args.get('cached')
    request_cached = False if not cache_arg \
                              or cache_arg and cache_arg.lower() == 'false' \
        else True

    if request_cached or cached:
        cache_route = REFERENCES['routes']['datalab_init']
        cached_val = Cache.get(cache_route)
        if not cached_val:
            Cache.cache_datalab_init()
            cached_val = Cache.get(cache_route)
        return cached_val
    else:
        json_obj = DatalabData.datalab_init()
        return ApiResult(json_obj)

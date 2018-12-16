"""Routes for API collections."""
from flask import request, url_for

from . import api
from pma_api.response import QuerySetApiResult
from pma_api.models import Country, EnglishString, Survey, Indicator, Data


@api.route('/countries')
def get_countries():
    """Country resource collection GET method.

    .. :quickref: Countries; Get collection of countries.

    Args:
        Non-REST, Python API for function has no arguments.

    Query Args:
        None

    Returns:
        json: Collection for resource.

    Details:
        Gets a list of all PMA2020 countries with publicly available data.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/countries
           :name: example-of-collection-countries

            {
              "metadata": {
                "..."
              },
              "resultSize": 10,
              "results": [
                {
                  "id": "BF",
                  "label": "Burkina Faso",
                  "order": 1,
                  "region": "Africa",
                  "subregion": "Western Africa"
                },
                "..."
              ]
            }
    """
    countries = Country.query.all()
    data = [c.full_json() for c in countries]
    return QuerySetApiResult(data, 'json')


@api.route('/countries/<code>')  # TODO: docstring when functional
def get_country(code):
    """Country resource entity GET method.

    .. :quickref: Countries; Access a specific country by its code.

    Args:
        code (str): Identification for resource entity.

    Query Args:
        None

    Returns:
        json: Entity of resource.

    Details:
        Access a specific PMA2020 country with publicly available data, by its
        code.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/countries/CODE
           :name: example-of-instance-country

            {"Documentation example not available."}
    """
    lang = request.args.get('_lang')
    country = Country.query.filter_by(country_code=code).first()
    json_obj = country.to_json(lang=lang)
    return QuerySetApiResult(json_obj, 'json')


@api.route('/surveys')
def get_surveys():
    """Survey resource collection GET method.

    .. :quickref: Survey rounds; Get collection of survey rounds.

    Args:
        Non-REST, Python API for function has no arguments.

    Query Args:
        None

    Returns:
        json: Collection for resource.

    Details:
        Gets a list of all PMA2020 country survey rounds with publicly
        available data.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/surveys
           :name: example-of-collection-surveys

            {
              "metadata": {
                "..."
              },
              "resultSize": 48,
              "results": [
                {
                  "country.id": "GH",
                  "country.label": "Ghana",
                  "country.order": 4,
                  "country.region": "Africa",
                  "country.subregion": "Western Africa",
                  "end_date": "2013-10-01",
                  "id": "PMA2013_GHR1",
                  "order": 101,
                  "pma_code": "GHR1",
                  "round": 1,
                  "start_date": "2013-09-01",
                  "type": "PMA2020",
                  "year": 2013
                },
                "..."
              ]
            }
    """
    # Query by year, country, round
    # print(request.args)
    surveys = Survey.query.all()
    data = [s.full_json() for s in surveys]
    return QuerySetApiResult(data, 'json')


@api.route('/surveys/<code>')
def get_survey(code):
    """Survey resource entity GET method.

    .. :quickref: Survey rounds; Access a specific survey round by its code

    Args:
        code (str): Identification for resource entity.

    Query Args:
        None

    Returns:
        json: Entity of resource.

    Details:
        Access a specific PMA2020 country survey round with publicly
        available data, by its code.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/surveys/PMA2013_GHR1
           :name: example-of-instance-survey

            {
              "metadata": {
                "..."
              },
              "resultSize": 13,
              "results": {
                "country.id": "GH",
                "country.label": "Ghana",
                "country.order": 4,
                "country.region": "Africa",
                "country.subregion": "Western Africa",
                "end_date": "2013-10-01",
                "id": "PMA2013_GHR1",
                "order": 101,
                "pma_code": "GHR1",
                "round": 1,
                "start_date": "2013-09-01",
                "type": "PMA2020",
                "year": 2013
              }
            }
    """
    survey = Survey.query.filter_by(code=code).first()
    json_obj = survey.full_json()
    return QuerySetApiResult(json_obj, 'json')


@api.route('/indicators')
def get_indicators():
    """Get Indicator resource collection.

    .. :quickref: Indicators; Get collection of available indicators.

    Args:
        Non-REST, Python API for function has no arguments.

    Query Args:
        None

    Returns:
        json: Collection for resource.

    Details:
        Gets a list of all PMA2020 indicators with publicly available data.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/indicators
           :name: example-of-collection-indicators

            {
              "metadata": {
                "..."
              },
              "resultSize": 112,
              "results": [
                {
                  "definition": "Percent of women ages 15\u201349 who are using (or whose partners are using) any contraceptive method at the time of the survey",
                  "denominator": "All women, ages 15-49",
                  "domain": "Women's reproductive health",
                  "favoriteOrder": 1,
                  "id": "cp_all",
                  "isFavorite": true,
                  "label": "Current use of any contraceptive method (all women)",
                  "level1": "Family planning utilization",
                  "level2": "Contraceptive use",
                  "measurementType": "percent",
                  "order": 11,
                  "type": "indicator",
                  "url": "http://api.pma2020.org/v1/indicators/cp_all"
                },
                "..."
              ]
            }
    """
    indicators = Indicator.query.all()
    data = [i.full_json(endpoint='api.get_indicator') for i in indicators]
    return QuerySetApiResult(data, 'json')


@api.route('/indicators/<code>')
def get_indicator(code):
    """Get Indicator resource entity.

    .. :quickref: Indicators; Access a specific indicator by its code

    Args:
        code (str): Identification for resource entity.

    Query Args:
        None

    Returns:
        json: Entity of resource.

    Details:
        Access a specific PMA2020 indicator with publicly available data, by
        its code.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/indicators/CODE
           :name: example-of-instance-indicator

            {
              "metadata": {
                "..."
              },
              "resultSize": 12,
              "results": {
                "definition": "Percent of women ages 15\u201349 who are using (or whose partners are using) any contraceptive method at the time of the survey",
                "denominator": "All women, ages 15-49",
                "domain": "Women's reproductive health",
                "favoriteOrder": 1,
                "id": "cp_all",
                "isFavorite": true,
                "label": "Current use of any contraceptive method (all women)",
                "level1": "Family planning utilization",
                "level2": "Contraceptive use",
                "measurementType": "percent",
                "order": 11,
                "type": "indicator"
              }
            }
    """
    indicator = Indicator.query.filter_by(code=code).first()
    json_obj = indicator.full_json()
    return QuerySetApiResult(json_obj, 'json')


@api.route('/data')  # TODO: docstring when functional
def get_data():
    """Get Data resource collection.

    .. :quickref: Data; Access de-identified survey data.

    Args:
        Non-REST, Python API for function has no arguments.

    Query Args:
        None

    Returns:
        json: Collection for resource.

    Details:
        Query de-identified PMA2020 survey data.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/data
           :name: example-of-collection-data

            {"Documentation example not available."}
    """
    all_data = data_refined_query(request.args)
    data = [d.full_json() for d in all_data]
    return QuerySetApiResult(data, 'json')


def data_refined_query(args):
    """Refine data query.

    Args:
        args: List of args. If 'survey' present, filter by survey entities.

    Query Args:
        None

    Returns:
        dict: Filtered query data.
    """
    qset = Data.query
    if 'survey' in args:
        qset = qset.filter(Data.survey.has(code=args['survey']))
    results = qset.all()
    return results


@api.route('/data/<code>')  # TODO: docstring when functional
def get_datum(code):
    """Get data resource entity.

    .. :quickref: Data; Access a specific datum by its code.

    Args:
        code (str): Identification for resource entity.

    Query Args:
        None

    Returns:
        json: Entity of resource.

    Details:
        Access a specific data record, by its code.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/data/CODE
           :name: example-of-instance-datum

            {"Documentation example not available."}
    """
    data = Data.query.filter_by(code=code).first()
    json_obj = data.full_json()
    return QuerySetApiResult(json_obj, 'json')


@api.route('/texts')
def get_texts():
    """Get Text resource collection.

    .. :quickref: Text; Get collection of various text related to surveys and
     metadata.

    Args:
        Non-REST, Python API for function has no arguments.

    Query Args:
        None

    Returns:
        json: Collection for resource.

    Details:
        Get a list of various texts related to surveys and metadata. Default
        language displayed is English (en).

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/texts
           :name: example-of-collection-texts

            {
              "metadata": {
                "..."
              },
              "resultSize": 515,
              "results": [
                {
                  "id": "6EA0At85",
                  "langCode": "en",
                  "text": "Kinshasa Province"
                },
                {
                  "id": "K9pC3w90",
                  "langCode": "en",
                  "text": "2013 Round 1"
                },
                {
                  "id": "0G2e7W61",
                  "langCode": "en",
                  "text": "Household / female questionnaire"
                },
                {
                  "id": "noFfI-js",
                  "langCode": "en",
                  "text": "Marital status"
                },
                {
                  "id": "qWyhZCgY",
                  "langCode": "en",
                  "text": "Married vs unmarried"
                },
                "..."
              ]
            }
    """
    english_strings = EnglishString.query.all()
    data = [d.to_json() for d in english_strings]
    return QuerySetApiResult(data, 'json')


@api.route('/texts/<code>')
def get_text(code):
    """Get Text resource entity.

    .. :quickref: Text; Access a specific piece of text by its code

    Args:
        code (str): Identification for resource entity.

    Query Args:
        None

    Returns:
        json: Entity of resource.

    Details:
        Access a specific piece of text related to surveys and metadata, by its
        code.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/texts/6EA0At85
           :name: example-of-instance-text

            {
              "metadata": {
                "..."
              },
              "resultSize": 3,
              "results": {
                "id": "6EA0At85",
                "langCode": "en",
                "text": "Kinshasa Province"
              }
            }
    """
    text = EnglishString.query.filter_by(code=code).first()
    json_obj = text.to_json()
    return QuerySetApiResult(json_obj, 'json')


# TODO: (jef/jkp 2017-08-29) Finish route. Needs: Nothing?
@api.route('/characteristicGroups')
def get_characteristic_groups():
    """Get Characteristic Groups resource collection.

    .. :quickref: Characteristic groups; Get collection of characteristic
     groups for disaggregation of data.

    Args:
        Non-REST, Python API for function has no arguments.

    Query Args:
        None

    Returns:
        json: Collection for resource.

    Details:
        Get a list of available PMA2020 characteristic groups for the
        disaggregation of data. **Unavailable in current version of API.**
    """
    from flask import jsonify
    return jsonify({'info': 'This endpoint has not yet been implemented.'})


@api.route('/characteristicGroups/<code>')  # TODO: docstring when functional
def get_characteristic_group(code):
    """Get Characteristic Groups resource entity.

    .. :quickref: Characteristic groups; Access a specific characteristic
     group by its code.

    Args:
        code (str): Identification for resource entity.

    Query Args:
        None

    Returns:
        json: Entity of resource.

    Details:
        Access a specific PMA2020 characteristic group for the disaggregation
        of data, by its code.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/characteristicGroups/CODE
           :name: example-of-instance-characteristicGroup

            {"Documentation example not available."}
    """
    return code


@api.route('/resources')  # TODO: Should show "url", not "resource".
def get_resources():
    """Return API resource routes.

    .. :quickref: Resources list; Lists all of the available API resources and
     their URLs.

    Args:
        Non-REST, Python API for function has no arguments.

    Query Args:
        None

    Returns:
        json: List of resources.

    Details:
        The resources object returned is split up into two main parts--results,
        and metadata. The metadata object contains information about the
        datasets used, including the client-specific "ui" dataset. The results
        object is the main object, which returns a list of resources,
        consisting of the resource name and its URL. The resource can then be
        accessed by using the literal URL string shown.

    Example:
        .. code-block:: json
           :caption: GET http://api.pma2020.org/v1/resources
           :name: example-of-collection-resources

            {
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
              "resultSize": 1,
              "results": {
                "resources": [
                  {
                    "name": "countries",
                    "resource": "http://api.pma2020.org/v1/countries"
                  },
                  {
                    "name": "surveys",
                    "resource": "http://api.pma2020.org/v1/surveys"
                  },
                  {
                    "name": "texts",
                    "resource": "http://api.pma2020.org/v1/texts"
                  },
                  {
                    "name": "indicators",
                    "resource": "http://api.pma2020.org/v1/indicators"
                  },
                  {
                    "name": "data",
                    "resource": "http://api.pma2020.org/v1/data"
                  },
                  {
                    "name": "characteristicGroups",
                    "resource": "http://api.pma2020.org/v1/characteristicGroups"
                  }
                ]
              }
            }
    """
    resource_endpoints = (
        ('countries', 'api.get_countries'),
        ('surveys', 'api.get_surveys'),
        ('texts', 'api.get_texts'),
        ('indicators', 'api.get_indicators'),
        ('data', 'api.get_data'),
        ('characteristicGroups', 'api.get_characteristic_groups')
    )
    json_obj = {
        'resources': [
            {
                'name': name,
                'resource': url_for(route, _external=True)
            }
            for name, route in resource_endpoints
        ]
    }
    return QuerySetApiResult(json_obj, 'json')

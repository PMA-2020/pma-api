"""Routes for API collections."""
from flask import request, url_for, redirect

from . import api
from ..response import QuerySetApiResult
from ..models import Country, EnglishString, Survey, Indicator, Data


@api.route('/countries')
def get_countries():
    """Country resource collection GET method.

    .. :quickref: Countries; Get collection of countries.

    Returns:
        json: Collection for resource.
    """
    countries = Country.query.all()
    data = [c.full_json() for c in countries]
    return QuerySetApiResult(data, 'json')


@api.route('/countries/<code>')
def get_country(code):
    """Country resource entity GET method.

    .. :quickref: Countries; Access a specific country by its code.

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    lang = request.args.get('_lang')
    country = Country.query.filter_by(country_code=code).first()
    json_obj = country.to_json(lang=lang)
    return QuerySetApiResult(json_obj, 'json')


@api.route('/surveys')
def get_surveys():
    """Survey resource collection GET method.

    .. :quickref: Survey rounds; Get collection of survey rounds.

    Returns:
        json: Collection for resource.
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

    Returns:
        json: Entity of resource.
    """
    survey = Survey.query.filter_by(code=code).first()
    json_obj = survey.full_json()
    return QuerySetApiResult(json_obj, 'json')


@api.route('/indicators')
def get_indicators():
    """Get Indicator resource collection.

    .. :quickref: Indicators; Get collection of available indicators.

    Returns:
        json: Collection for resource.
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

    Returns:
        json: Entity of resource.
    """
    indicator = Indicator.query.filter_by(code=code).first()
    json_obj = indicator.full_json()
    return QuerySetApiResult(json_obj, 'json')


@api.route('/data')
def get_data():
    """Get Data resource collection.

    .. :quickref: Data; Access de-identified survey data.

    Returns:
        json: Collection for resource.
    """
    all_data = data_refined_query(request.args)
    data = [d.full_json() for d in all_data]
    return QuerySetApiResult(data, 'json')


def data_refined_query(args):
    """Refine data query.

    Args:
        args: List of args. If 'survey' present,
        filter by survey entities.

    Returns:
        dict: Filtered query data.
    """
    qset = Data.query
    if 'survey' in args:
        qset = qset.filter(Data.survey.has(code=args['survey']))
    results = qset.all()
    return results


@api.route('/data/<code>')
def get_datum(code):
    """Get data resource entity.

    .. :quickref: Data; Access a specific datum by its code.

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    data = Data.query.filter_by(code=code).first()
    json_obj = data.full_json()
    return QuerySetApiResult(json_obj, 'json')


@api.route('/texts')
def get_texts():
    """Get Text resource collection.

    .. :quickref: Text; Get collection of various text related to surveys and
     metadata.

    Returns:
        json: Collection for resource.
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

    Returns:
        json: Entity of resource.
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

    Returns:
        json: Collection for resource.
    """
    from flask import jsonify
    return jsonify({'info': 'To be implemented.'})


@api.route('/characteristicGroups/<code>')
def get_characteristic_group(code):
    """Get Characteristic Groups resource entity.

    .. :quickref: Characteristic groups; Access a specific characteristic
     group by its code.

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    return code


@api.route('/resources')
def get_resources():
    """Return API resource routes.

    .. :quickref: Resources list; Lists all of the available API resources and
     their URLs.

    Returns:
        json: List of resources.
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

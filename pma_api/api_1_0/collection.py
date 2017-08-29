"""Routes for API collections."""
from flask import request, url_for

from . import api
from .response import response
from ..models import Country, EnglishString, Survey, Indicator, Data


@api.route('/countries')
def get_countries():
    """Country resource collection GET method.

    Returns:
        json: Collection for resource.
    """
    model = Country
    countries = model.query.all()

    print('\n\n', request.args)  # Testing
    validity, messages = model.validate_query(request.args)
    print(validity)
    print(messages)
    print('\n\n')

    return response(request_args=request.args, data={
        'resultsSize': len(countries),
        'results': [c.full_json() for c in countries]
    })


@api.route('/countries/<code>')
def get_country(code):
    """Country resource entity GET method.

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    lang = request.args.get('_lang')
    country = Country.query.filter_by(country_code=code).first()
    json_obj = country.to_json(lang=lang)
    return response(request_args=request.args, data=json_obj)


@api.route('/surveys')
def get_surveys():
    """Survey resource collection GET method.

    Returns:
        json: Collection for resource.
    """
    # Query by year, country, round
    # print(request.args)
    surveys = Survey.query.all()
    return response(request_args=request.args, data={
        'resultsSize': len(surveys),
        'results': [s.full_json() for s in surveys]
    })


@api.route('/surveys/<code>')
def get_survey(code):
    """Survey resource entity GET method.

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    survey = Survey.query.filter_by(code=code).first()
    json_obj = survey.full_json()
    return response(request_args=request.args, data=json_obj)


@api.route('/indicators')
def get_indicators():
    """Get Indicator resource collection.

    Returns:
        json: Collection for resource.
    """
    indicators = Indicator.query.all()
    return response(request_args=request.args, data={
        'resultsSize': len(indicators),
        'results': [
            i.full_json(endpoint='api.get_indicator') for i in indicators
        ]
    })


@api.route('/indicators/<code>')
def get_indicator(code):
    """Get Indicator resource entity.

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    indicator = Indicator.query.filter_by(code=code).first()
    json_obj = indicator.full_json()
    return response(request_args=request.args, data=json_obj)


@api.route('/data')
def get_data():
    """Get Data resource collection.

    Returns:
        json: Collection for resource.
    """
    all_data = data_refined_query(request.args)
    # all_data = Data.query.all()
    return response(request_args=request.args, data={
        'resultsSize': len(all_data),
        'results': [d.full_json() for d in all_data]
    })


def data_refined_query(args):
    """Refine data query.

    *Args:
        survey (str): If present, filter by survey entities.

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

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    data = Data.query.filter_by(code=code).first()
    json_obj = data.full_json()
    return response(request_args=request.args, data=json_obj)


@api.route('/texts')
def get_texts():
    """Get Text resource collection.

    Returns:
        json: Collection for resource.
    """
    english_strings = EnglishString.query.all()
    return response(request_args=request.args, data={
        'resultsSize': len(english_strings),
        'results': [d.to_json() for d in english_strings]
    })


@api.route('/texts/<code>')
def get_text(code):
    """Get Text resource entity.

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    text = EnglishString.query.filter_by(code=code).first()
    json_obj = text.to_json()
    return response(request_args=request.args, data=json_obj)


@api.route('/characteristicGroups')
def get_characteristic_groups():
    """Get Characteristic Groups resource collection.

    Returns:
        json: Collection for resource.
    """
    return 'Characteristic groups'  # TODO


@api.route('/characteristicGroups/<code>')
def get_characteristic_group(code):
    """Get Characteristic Groups resource entity.

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    return code


@api.route('/resources')
def get_resources():
    """Return API resource routes.

    Returns:
        json: List of resources.
    """
    resource_endpoints = (
        ('countries', 'api.get_surveys'),
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
    return response(request_args=request.args, data=json_obj)

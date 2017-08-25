"""API Routes."""
from flask import Blueprint, jsonify, request, url_for

from ..queries import DatalabData
from ..models import Country, EnglishString, Survey, Indicator, Data


api = Blueprint('api', __name__)


@api.route('/')
def root():
    """Root route.

    Returns:
        func: get_resources() if 'application/json'
        func: get_docs() if 'text/html'
    """
    # TODO: See flask.pocoo.org/snippets/45/
    request_headers = 'application/json'  # default for now
    if request_headers == 'text/html':
        return 'Documentation.'
    return get_resources()


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

    return jsonify({
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
    return jsonify(json_obj)


@api.route('/surveys')
def get_surveys():
    """Survey resource collection GET method.

    Returns:
        json: Collection for resource.
    """
    # Query by year, country, round
    # print(request.args)
    surveys = Survey.query.all()
    return jsonify({
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
    return jsonify(json_obj)


@api.route('/indicators')
def get_indicators():
    """Indicator resource collection GET method.

    Returns:
        json: Collection for resource.
    """
    indicators = Indicator.query.all()
    return jsonify({
        'resultsSize': len(indicators),
        'results': [
            i.full_json(endpoint='api.get_indicator') for i in indicators
        ]
    })


@api.route('/indicators/<code>')
def get_indicator(code):
    """Indicator resource entity GET method.

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    indicator = Indicator.query.filter_by(code=code).first()
    json_obj = indicator.full_json()
    return jsonify(json_obj)


@api.route('/data')
def get_data():
    """Data resource collection GET method.

    Returns:
        json: Collection for resource.
    """
    all_data = data_refined_query(request.args)
    # all_data = Data.query.all()
    return jsonify({
        'resultsSize': len(all_data),
        'results': [d.full_json() for d in all_data]
    })


def data_refined_query(args):
    """Data refined query.

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
    """Data resource entity GET method.

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    data = Data.query.filter_by(code=code).first()
    json_obj = data.full_json()
    return jsonify(json_obj)


@api.route('/texts')
def get_texts():
    """Text resource collection GET method.

    Returns:
        json: Collection for resource.
    """
    english_strings = EnglishString.query.all()
    return jsonify({
        'resultsSize': len(english_strings),
        'results': [d.to_json() for d in english_strings]
    })


@api.route('/texts/<code>')
def get_text(code):
    """Text resource entity GET method.

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    text = EnglishString.query.filter_by(code=code).first()
    json_obj = text.to_json()
    return jsonify(json_obj)


@api.route('/characteristicGroups')
def get_characteristic_groups():
    """Characteristic Groups  resource collection GET method.

    Returns:
        json: Collection for resource.
    """
    return 'Characteristic groups'  # TODO


@api.route('/characteristicGroups/<code>')
def get_characteristic_group(code):
    """Characteristic Groups resource entity GET method.

    Args:
        code (str): Identification for resource entity.

    Returns:
        json: Entity of resource.
    """
    return code


@api.route('/resources')
def get_resources():
    """API resource route.

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
    return jsonify(json_obj)


# TODO: Handle null cases.
@api.route('/datalab/data')
def get_datalab_data():
    """Get the correct slice of datalab data."""
    if not request.args:
        json_obj = DatalabData.get_all_datalab_data()
    elif 'survey' not in request.args or 'indicator' not in request.args \
            or 'characteristicGroup' not in request.args:
        return 'InvalidArgsError: This endpoint requires the following 3 ' \
               'parameters: \n* survey\n* indicator\n* characteristicGroup'
    else:
        survey = request.args.get('survey', None)
        indicator = request.args.get('indicator', None)
        char_grp = request.args.get('characteristicGroup', None)
        json_obj = DatalabData.get_filtered_datalab_data(survey, indicator,
                                                         char_grp)

    return jsonify(json_obj)


@api.route('/datalab/combos')
def get_datalab_combos():
    """Get datalab combos."""
    # TODO: Account for all combinations of request args or lack thereof.
    # TODO: Add logic to sort by arguments. If you have indicator, go to
    # this method.

    if 'survey' not in request.args and 'indicator' not in request.args \
            and 'characteristicGroup' not in request.args:
        return 'InvalidArgsError: This endpoint requires 1-2 of 3 ' \
               'parameters: \n* survey\n* indicator\n* characteristicGroup'

    # return jsonify(DatalabData.related_models_from_single_model_data(
    #     request.args))
    return jsonify(DatalabData.get_combos(request.args))


@api.route('/datalab/init')
def get_datalab_init():
    """Get datalab combos."""
    return jsonify(DatalabData.datalab_init())

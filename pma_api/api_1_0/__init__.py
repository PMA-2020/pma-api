from flask import Blueprint, jsonify, request, url_for

from ..models import Country, EnglishString, Survey, Indicator, Data


api = Blueprint('api', __name__)


@api.route('/')
def say_hello():
    return '<h1>HELLO FLASK</h1>'


@api.route('/countries')
def get_countries():
    countries = Country.query.all()
    return jsonify({
        'resultsSize': len(countries),
        'results': [c.full_json() for c in countries]
    })


@api.route('/countries/<code>')
def get_country(code):
    lang = request.args.get('_lang')
    country = Country.query.filter_by(country_code=code).first()
    json_obj = country.to_json(lang=lang)
    return jsonify(json_obj)


@api.route('/surveys')
def get_surveys():
    # Query by year, country, round
    # print(request.args)
    surveys = Survey.query.all()
    return jsonify({
        'resultsSize': len(surveys),
        'results': [s.full_json() for s in surveys]
    })


@api.route('/surveys/<code>')
def get_survey(code):
    survey = Survey.query.filter_by(code=code).first()
    json_obj = survey.full_json()
    return jsonify(json_obj)


@api.route('/indicators')
def get_indicators():
    indicators = Indicator.query.all()
    return jsonify({
        'resultsSize': len(indicators),
        'results': [
            i.full_json(endpoint='api.get_indicator') for i in indicators
        ]
    })


@api.route('/indicators/<code>')
def get_indicator(code):
    indicator = Indicator.query.filter_by(code=code).first()
    json_obj = indicator.full_json()
    return jsonify(json_obj)


@api.route('/characteristics')
def get_characterstics():
    pass


@api.route('/characteristics/<code>')
def get_characteristic(code):
    pass


@api.route('/data')
def get_data():
    # all_data = data_refined_query(request.args)  # TODO: Put this back.
    all_data = Data.query.all()
    return jsonify(json_obj = {
        'resultsSize': len(all_data),
        'results': [d.full_json() for d in all_data]
    })


def data_refined_query(args):
    qset = Data.query
    if 'survey' in args:
        qset = qset.filter(Data.survey.has(code=args['survey']))
    results = qset.all()
    return results

@api.route('/data/<uuid>')
def get_datum(uuid):
    data = Data.query.filter_by(code=uuid).first()
    json_obj = data.full_json()
    return jsonify(json_obj)


@api.route('/texts')
def get_texts():
    english_strings = EnglishString.query.all()
    return jsonify(json_obj = {
        'resultsSize': len(english_strings),
        'results': [d.to_json() for d in english_strings]
    })



@api.route('/texts/<uuid>')
def get_text(uuid):
    text = EnglishString.query.filter_by(uuid=uuid).first()
    json_obj = text.to_json()
    return jsonify(json_obj)


@api.route('/resources')
def get_resources():
    return jsonify({
        'resources': [{
            'name': 'countries',
            'resource': url_for('api.get_surveys', _external=True)
        },{
            'name': 'surveys',
            'resource': url_for('api.get_countries', _external=True)
        },{
            'name': 'texts',
            'resource': url_for('api.get_texts', _external=True)
        }]
    })

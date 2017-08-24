"""Queries."""
from sqlalchemy import or_
from sqlalchemy.orm import aliased

from . import db
from .models import Data, Survey, Indicator, Characteristic, \
    CharacteristicGroup


class DatalabData:
    """PmaData"""
    model = Data
    char1 = aliased(Characteristic)
    char2 = aliased(Characteristic)
    char_grp1 = aliased(CharacteristicGroup)
    char_grp2 = aliased(CharacteristicGroup)
    default_display_fields = (Survey.code, Indicator.code, char1.code,
                              char_grp1.code)
    model_info = {
        # - Note: model_info key meanings.
        # '<model_name>': {
        #     'model': '<SqlAlchemy Model Class>',
        #     'index': '<SqlAlchemy Query Index>'
        # },
        'data': {
            'db_name': 'data',
            'api_name': 'data',
            'model': Data,
            'index': 0
        },
        'survey': {
            'db_name': 'survey',
            'api_name': 'survey',
            'model': Survey,
            'index': 1
        },
        'indicator': {
            'db_name': 'indicator',
            'api_name': 'indicator',
            'model': Indicator,
            'index': 2
        },
        'characteristic': {
            'db_name': 'characteristic',
            'api_name': 'characteristic',
            'model': Characteristic,
            'index': 3
        },
        'characteristicGroup': {
            'db_name': 'characteristic_group',
            'api_name': 'characteristicGroup',
            'model': CharacteristicGroup,
            'index': 4
        }
    }
    combo_models = ('survey', 'indicator', 'characteristicGroup')

    @staticmethod
    def default_data_view():
        """Default data view."""
        return \
            DatalabData.datalab_data_view(DatalabData.default_display_fields)

    @staticmethod
    def all_combinable_model_indices():
        """All combo model indices."""
        return [DatalabData.model_info[x]['index'] for x in
                DatalabData.combo_models]

    @staticmethod
    def remaining_model_indices(this_model_name):
        """Remaining combo model indices."""
        this_model_index = DatalabData.model_info[this_model_name]['index']
        return tuple(x for x in DatalabData.all_combinable_model_indices()
                     if x != this_model_index)

    @staticmethod
    def remaining_model_names(this_model_name):
        """Remaining combo model names."""
        return tuple(x for x in DatalabData.combo_models
                     if x != this_model_name)

    @staticmethod
    def remaining_model_name_indices(this_model_name):
        """Remaining combo model names and indices."""
        other_model_indices, other_model_names = \
            DatalabData.remaining_model_indices(this_model_name), \
            DatalabData.remaining_model_names(this_model_name)
        return {k: v for k, v in zip(other_model_names, other_model_indices)}

    @staticmethod
    def model_index(model_name):
        """Get model index."""
        return DatalabData.model_info[model_name]['index']

    @staticmethod
    def results_with_size(results):
        """Results with size."""
        return {
            'resultsSize': len(results),
            'results': results
        }

    @staticmethod
    def format_response(query_result):
        """Format response"""
        index = DatalabData.model_index
        json_results = []
        for record in query_result:
            this_dict = {
                'value': record[index('data')].value,
                'precision': record[index('data')].precision,
                'survey.id': record[index('survey')],
                'indicator.id': record[index('indicator')],
                'characteristic.id': record[index('characteristic')],
                'characteristicGroup.id': record[index('characteristicGroup')]
            }
            json_results.append(this_dict)
        return DatalabData.results_with_size(json_results)

    @staticmethod
    def api_list_to_sql_list(model, query_values):
        """Survey list to SQL."""
        # TODO: Error checking on survey_list.
        split = query_values.split(',')
        sql_exprs = [model.code == code for code in split]
        if len(sql_exprs) > 1:
            full_sql = or_(*sql_exprs)
        else:
            full_sql = sql_exprs[0]
        return full_sql

    @staticmethod
    def datalab_data_view(display_fields):
        """Joined table."""
        mdl, chr1, chr2, grp1, grp2 = \
            DatalabData.model, DatalabData.char1, DatalabData.char2, \
            DatalabData.char_grp1, DatalabData.char_grp2

        joined = db.session.query(mdl, *display_fields) \
            .join(Survey, mdl.survey_id == Survey.id) \
            .join(Indicator, mdl.indicator_id == Indicator.id) \
            .outerjoin(chr1, mdl.char1_id == chr1.id) \
            .outerjoin(grp1, grp1.id == chr1.char_grp_id) \
            .outerjoin(chr2, mdl.char2_id == chr2.id) \
            .outerjoin(grp2, grp2.id == chr2.char_grp_id)

        return joined

    @staticmethod
    def get_all_datalab_data():
        """Get all datalab data."""
        results = DatalabData.default_data_view().all()
        return DatalabData.format_response(results)

    @staticmethod
    def get_filtered_datalab_data(survey_codes, indicator_code,
                                  char_grp1_code):
        """Get filtered datalab data."""
        survey_sql = DatalabData.api_list_to_sql_list(
            model=Survey, query_values=survey_codes)
        grp1, grp2 = DatalabData.char_grp1, DatalabData.char_grp2

        # TODO: Pylint ignore E711 - Comparison to 'None' should be 'is'.
        results = DatalabData.default_data_view().filter(survey_sql) \
            .filter(Indicator.code == indicator_code) \
            .filter(grp1.code == char_grp1_code) \
            .filter(grp2.code == None) \
            .all()

        return DatalabData.format_response(results)

    @staticmethod
    def other_model_codes(this_model_name, filter_codes):
        """Get other combinable model codes."""
        # TODO: Question, should we return 'null' as is, or otherwise?
        # TODO: How to search the DB by 'null' if the user asks for it?

        other_model_name_indices = DatalabData.\
            remaining_model_name_indices(this_model_name)
        results = DatalabData.default_data_view().filter(filter_codes).all()
        combos = {k: list(set(record[v] for record in results))  # Model codes
                  for k, v in other_model_name_indices.items()}

        return combos

    @staticmethod
    def get_combos(request_args):
        """Get other combinable model codes."""
        query_keys = tuple(k for k, v in request_args.items())

        if len(query_keys) == 1:
            mdl = DatalabData.model_info[query_keys[0]]
            codes = DatalabData.api_list_to_sql_list(
                model=mdl['model'], query_values=request_args[mdl['api_name']])

            return DatalabData.other_model_codes(
                this_model_name=mdl['api_name'], filter_codes=codes)

        # return 'Only supporting one query parameter at the moment.'
        # - WIP
        result = DatalabData.get_filtered_datalab_data(
            survey_codes=request_args['survey']
            if request_args['survey'] else None,
            indicator_code=request_args['indicator']
            if request_args['indicator'] else None,
            char_grp1_code=request_args['characteristicGroup']
            if request_args['characteristicGroup'] else None)

        return result

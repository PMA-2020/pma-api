"""Queries."""
from collections import ChainMap

from sqlalchemy import or_, distinct
from sqlalchemy.orm import aliased

from . import db
from .models import Data, Survey, Indicator, Characteristic, \
    CharacteristicGroup, EnglishString, Translation


# TODO: Include query parameters inside the response.
class DatalabData:
    """PmaData"""
    model = Data
    char1 = aliased(Characteristic)
    char2 = aliased(Characteristic)
    char_grp1 = aliased(CharacteristicGroup)
    char_grp2 = aliased(CharacteristicGroup)
    default_display_fields = (Survey.code, Indicator.code, char1.code,
                              char_grp1.code)
    # TODO: Use aliases instead of indexes.
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
    def datalab_data_joined(*select_args):
        """Datalab data joined."""
        chr1 = DatalabData.char1
        chr2 = DatalabData.char2
        grp1 = DatalabData.char_grp1
        grp2 = DatalabData.char_grp2
        # joined = Data\
        # joined = db.session.query(*select_args)\
        # .select_from(Data)
        joined = db.session.query(*select_args)\
            .select_from(Data) \
            .join(Survey, Data.survey_id == Survey.id) \
            .join(Indicator, Data.indicator_id == Indicator.id) \
            .outerjoin(chr1, Data.char1_id == chr1.id) \
            .outerjoin(grp1, grp1.id == chr1.char_grp_id) \
            .outerjoin(chr2, Data.char2_id == chr2.id) \
            .outerjoin(grp2, grp2.id == chr2.char_grp_id)
        return joined

    @staticmethod
    def datalab_data_view(display_fields):
        """Joined table."""
        select_args = [DatalabData.model, *display_fields]
        return DatalabData.datalab_data_joined(*select_args)

    @staticmethod
    def get_combo_from_multiple_keys(survey_codes, indicator_code,
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
    def related_models_from_single_model_data(request_args):
        """Get other combinable model codes.

        This is useful for: Indicator, Characteristic Group.
        """
        query_keys = tuple(k for k, v in request_args.items())

        if len(query_keys) == 1:  # TODO: Refactor to something like
                                    # TODO: get_combos()
            mdl = DatalabData.model_info[query_keys[0]]
            codes = DatalabData.api_list_to_sql_list(
                model=mdl['model'], query_values=request_args[mdl['api_name']])

            return DatalabData.other_model_codes(
                this_model_name=mdl['api_name'], filter_codes=codes)
        else:
            # TODO RETURN SOMETHING
            return 'something went wrong related_models_from_single_model_data'

    # TODO: Finish this.
    @staticmethod
    def related_models_from_multi_model_data(indicator, char_grp):
        """Get other combinable model codes.

        This is useful for: Survey.
        """
        # grp1, grp2 = DatalabData.char_grp1, DatalabData.char_grp2
        # TODO: Pylint ignore E711 - Comparison to 'None' should be 'is'.
        select_args = distinct(Survey.code)
        results = DatalabData.datalab_data_joined(select_args)
        results = results.all()

        # results = DatalabData.default_data_view() \
        #     .filter(Indicator.code == indicator) \
        #     .filter(grp1.code == char_grp) \
        #     .filter(grp2.code == None) \
        #     .all()
        
        results = [item[0] for item in results]

        return results
        # return DatalabData.format_response(results)
        # pass

    @staticmethod
    def get_combos(request_args):
        """Get other combinable model codes."""
        # Calls another function of get combos with a survey code.
        survey_list = request_args.get('survey', None)
        indicator = request_args.get('indicator', None)
        char_grp = request_args.get('characteristicGroup', None)
        if survey_list and not indicator and not char_grp:
            return DatalabData.get_combos_survey_list(survey_list)
        elif not survey_list and indicator and char_grp:
            return DatalabData.related_models_from_multi_model_data(indicator,
                                                           char_grp)
        elif not survey_list and (indicator or char_grp):
            # TODO: Refactor passing in request_args to concretely passing in
            #       indicator and char_grp explicitly.
            return DatalabData.related_models_from_single_model_data(
                request_args)
        elif survey_list and indicator and char_grp:
            # TODO: Not a valid query
            return DatalabData.get_filtered_datalab_data(survey_list,
                                                         indicator, char_grp)
        elif survey_list and indicator and not char_grp:
            return DatalabData.get_combos_survey_indicator(survey_list,
                                                           indicator)
        elif survey_list and char_grp and not indicator:
            return DatalabData.get_combos_survey_char_grp(survey_list,
                                                           char_grp)
        else:
            return "Something unexpected happened."

    @staticmethod
    def get_combos_survey_list(survey_list):
        """Get combos for survey list."""
        survey_list_sql = DatalabData.api_list_to_sql_list(Survey, survey_list)
        select_args = (Indicator.code, DatalabData.char_grp1.code)
        joined = DatalabData.datalab_data_joined(*select_args)
        filtered = joined.filter(survey_list_sql)
        results = filtered.distinct().all()
        results = [{
            'indicator.id': record[0],
            'characteristicGroup.id': record[1]
        } for record in results]
        results = DatalabData.results_with_size(results)

        return results


    @staticmethod  # TODO: Finish: Results.all() returns an sequence for each
    #result. Therefore an iterable of sequence.
    def get_combos_survey_indicator(survey_list, indicator):
        """Get combos for survey list and indicator."""
        survey_list_sql = DatalabData.api_list_to_sql_list(Survey, survey_list)
        select_args = distinct(CharacteristicGroup.code)
        joined = DatalabData.datalab_data_joined(select_args)
        filtered = joined.filter(survey_list_sql)\
            .filter(Indicator.code == indicator)
        results = filtered.all()
        results = [x[0] for x in results]
        return results

    @staticmethod  # TODO: Fiish
    def get_combos_survey_char_grp(survey_list, char_grp):
        """Get combos for survey list and char group."""
        survey_list_sql = DatalabData.api_list_to_sql_list(Survey, survey_list)
        select_args = distinct(Indicator.code)
        joined = DatalabData.datalab_data_joined(select_args)
        filtered = joined.filter(survey_list_sql)\
            .filter(CharacteristicGroup.code == char_grp)
        results = filtered.all()
        results = [x[0] for x in results]
        return results

    @staticmethod
    def datalab_init_indicators():
        """Datalab init."""
        select_args = Indicator
        joined = DatalabData.datalab_data_joined(select_args)
        results = joined.distinct().all()
        results = [record.datalab_init_json() for record in results]
        return results

    @staticmethod
    def datalab_init_char_grp():
        """Datalab init."""
        select_args = DatalabData.char_grp1
        joined = DatalabData.datalab_data_joined(select_args)
        results = joined.distinct().all()
        results = [record.datalab_init_json() if record is not None else "none"
                   for record in results]
        return results


    @staticmethod
    def datalab_init_chars():
        """Datalab init."""
        select_args = DatalabData.char1
        joined = DatalabData.datalab_data_joined(select_args)
        results = joined.distinct().all()
        results = [record.datalab_init_json() if record is not None else "none"
                   for record in results]
        return results

    @staticmethod
    def datalab_init_surveys():
        """Datalab init."""
        select_args = Survey
        joined = DatalabData.datalab_data_joined(select_args)
        results = joined.distinct().all()
        results = [record.datalab_init_json() for record in results]

        return results

    @staticmethod  # TODO: Get other languages.
    def datalab_init_strings():
        """Datalab init."""
        results= EnglishString.query.all()
        results = [record.datalab_init_json() for record in results]
        results = dict(ChainMap(*results))
        return results

    @staticmethod
    def datalab_init_languages():
        """Datalab init."""
        return Translation.languages()

    @staticmethod
    def datalab_init():
        """DataLab Init."""
        return {
            'indicators': DatalabData.datalab_init_indicators(),
            'characteristicGroups': DatalabData.datalab_init_char_grp(),
            'characteristics': DatalabData.datalab_init_chars(),
            'surveys': DatalabData.datalab_init_surveys(),
            'strings': DatalabData.datalab_init_strings(),
            'languages': DatalabData.datalab_init_languages()
        }

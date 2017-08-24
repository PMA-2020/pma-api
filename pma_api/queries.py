"""Queries."""
from sqlalchemy import or_
from sqlalchemy.orm import aliased

from . import db
from .models import Data, Survey, Indicator, Characteristic, \
    CharacteristicGroup


def get_datalab_data():
    """Get datalab data."""
    char1 = aliased(Characteristic)
    char2 = aliased(Characteristic)
    char_grp1 = aliased(CharacteristicGroup)
    char_grp2 = aliased(CharacteristicGroup)
    data = (Data, Survey.code, Indicator.code, char1.code, char_grp1.code)
    joined = db.session.query(*data) \
               .join(Survey, Data.survey_id == Survey.id) \
               .join(Indicator, Data.indicator_id == Indicator.id) \
               .outerjoin(char1, Data.char1_id == char1.id) \
               .outerjoin(char_grp1, char_grp1.id == char1.char_grp_id) \
               .outerjoin(char2, Data.char2_id == char2.id) \
               .outerjoin(char_grp2, char_grp2.id == char2.char_grp_id)
    return joined


def get_filtered_datalab_data(survey_code, indicator_code, char_grp1_code):
    """Get filtered datalab data."""
    joined = get_datalab_data()

    char_grp1 = aliased(CharacteristicGroup)  # Duplicated
    char_grp2 = aliased(CharacteristicGroup)  # Duplicated

    survey_sql = survey_list_to_sql(survey_code)
    # results = joined.filter(survey_sql) \
    #                 .filter(Indicator.code == indicator_code) \
    #                 .filter(char_grp1.code == char_grp1_code) \
    #                 .filter(char_grp2.code is None) \
    #                 .all()

    results = joined.filter(Survey.code == 'GH2013PMA') \
                    .filter(Indicator.code == 'mcpr_aw') \
                    .filter(char_grp1.code == 'wealth_quintile') \
                    .filter(char_grp2.code is None) \
                    .all()

    return format_response(results)


def get_all_datalab_data():
    """Get all datalab data."""
    results = get_datalab_data().all()
    return format_response(results)


def format_response(query_result):
    """Format response"""
    json_results = []
    for record in query_result:
        this_dict = {
            'value': record[0].value,
            'precision': record[0].precision,
            'survey.id': record[1],
            'indicator.id': record[2],
            'characteristic.id': record[3],
            'characteristicGroup.id': record[4]
        }
        json_results.append(this_dict)
    return json_results


def survey_list_to_sql(survey_list):
    """Survey list to SQL."""
    # TODO: error checking on survey_list
    split = survey_list.split(',')
    sql_exprs = [Survey.code == code for code in split]
    if len(sql_exprs) > 1:
        full_sql = or_(*sql_exprs)
    else:
        full_sql = sql_exprs[0]
    return full_sql


# class PmaData:
#     char1 = aliased(Characteristic)
#     char2 = aliased(Characteristic)
#     char_grp1 = aliased(CharacteristicGroup)
#     char_grp2 = aliased(CharacteristicGroup)
#
#     @staticmethod
#     def joined_table(*args):
#         char1 = PmaData.char1
#         char2 = PmaData.char2
#         char_grp1 = PmaData.char_grp1
#         char_grp2 = PmaData.char_grp2
#         joined = db.session.query(*args) \
#             .join(Survey, Data.survey_id == Survey.id) \
#             .join(Indicator, Data.indicator_id == Indicator.id) \
#             .outerjoin(char1, Data.char1_id == char1.id) \
#             .outerjoin(char_grp1, char_grp1.id == char1.char_grp_id) \
#             .outerjoin(char2, Data.char2_id == char2.id) \
#             .outerjoin(char_grp2, char_grp2.id == char2.char_grp_id)
#         return joined
#
#     def get_datalab_data(a, b, c):
#         select = (
#         Data, Survey.code, Indicator.code, char1.code, char_grp1.code)
#         joined = PmaData.joined_table(select)
#         results = joined.filter(...).all()
#
#     def get_survey_char_grp_combos(survey_list):
#         # get survey_sql from survey_list
#         results = joined.filter(survey_sql).all()
#         to_return = set()
#         for record in results:
#             item = (record[2], record[4])
#             to_return.add(item)
#

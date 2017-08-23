"""Queries."""
from sqlalchemy import or_
from sqlalchemy.orm import aliased

from . import db
from .models import Data, Survey, Indicator, Characteristic, \
    CharacteristicGroup


def get_datalab_data(survey_code, indicator_code, char_grp1_code):
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
    survey_sql = survey_list_to_sql(survey_code)
    results = joined.filter(survey_sql) \
                    .filter(Indicator.code == indicator_code) \
                    .filter(char_grp1.code == char_grp1_code) \
                    .filter(char_grp2.code is None) \
                    .all()
    json_results = []
    for record in results:
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

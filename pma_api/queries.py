"""Queries."""
from collections import ChainMap

from sqlalchemy import or_
from sqlalchemy.orm import aliased

from . import db
from .models import (Characteristic, CharacteristicGroup, Data, EnglishString,
                     Indicator, Survey, Translation)


class DatalabData:
    """PmaData."""

    char1 = aliased(Characteristic)
    char2 = aliased(Characteristic)
    char_grp1 = aliased(CharacteristicGroup)
    char_grp2 = aliased(CharacteristicGroup)

    @staticmethod
    def all_joined(*select_args):
        """Datalab data joined."""
        chr1 = DatalabData.char1
        chr2 = DatalabData.char2
        grp1 = DatalabData.char_grp1
        grp2 = DatalabData.char_grp2
        joined = db.session.query(*select_args) \
            .select_from(Data) \
            .join(Survey, Data.survey_id == Survey.id) \
            .join(Indicator, Data.indicator_id == Indicator.id) \
            .outerjoin(chr1, Data.char1_id == chr1.id) \
            .outerjoin(grp1, grp1.id == chr1.char_grp_id) \
            .outerjoin(chr2, Data.char2_id == chr2.id) \
            .outerjoin(grp2, grp2.id == chr2.char_grp_id)
        return joined

    @staticmethod
    def filter_minimal(survey_codes, indicator_code, char_grp_code):
        """Get filtered Datalab data and return minimal columns.

        Args:
            survey_codes (str): A list of survey codes joined together by a
                comma
            indicator_code (str): An indicator code
            char_grp_code (str): A characteristic group code

        Filters the data based on the function arguments. The returned data
        are data value, the precision, the survey code, the indicator code,
        the characteristic group code, and the characteristic code.

        Returns:
            A list of simple python objects, one for each record found by
            applying the various filters.
        """
        chr1 = DatalabData.char1
        grp1, grp2 = DatalabData.char_grp1, DatalabData.char_grp2
        select_args = (Data, Survey.code, Indicator.code,
                       grp1.code, chr1.code)
        filtered = DatalabData.all_joined(*select_args)
        if survey_codes is not None:
            survey_sql = DatalabData.survey_list_to_sql(survey_codes)
            filtered = filtered.filter(survey_sql)
        if indicator_code is not None:
            filtered = filtered.filter(Indicator.code == indicator_code)
        if char_grp_code is not None:
            filtered = filtered.filter(grp1.code == char_grp_code)
        # TODO (jkp, begin=2017-08-28): This will be grp2.code == 'none'
        # eventually when the Data show "none" for char_grp2 in excel import
        # Remove E711 from .pycodestyle
        # pylint: disable=singleton-comparison
        filtered = filtered.filter(grp2.code == None)
        results = filtered.all()
        json_results = []
        for item in results:
            this_dict = {
                'value': item[0].value,
                'precision': item[0].precision,
                'survey.id': item[1],
                'indicator.id': item[2],
                'characteristicGroup.id': item[3],
                'characteristic.id': item[4]
            }
            json_results.append(this_dict)
        return json_results

    @staticmethod
    def survey_list_to_sql(survey_list):
        """Turn a list of surveys passed through URL to SQL.

        Args:
            survey_list (str): A list of survey codes

        Returns:
            The SQLAlchemy object that represents these OR'd together.
        """
        return DatalabData.api_list_to_sql_list(Survey, survey_list)

    @staticmethod
    def api_list_to_sql_list(model, query_values):
        """Convert generally query args to SQL.

        Args:
            model (db.Model): A model object with a code attribute
            query_values (str): A list of codes joined by comma

        Results:
            The SQLAlchemy object that represents these OR'd together.
        """
        # TODO (jkp 2017-08-28) Error checking on survey_list.
        split = query_values.split(',')
        sql_exprs = [model.code == code for code in split]
        if len(sql_exprs) > 1:
            full_sql = or_(*sql_exprs)
        else:
            full_sql = sql_exprs[0]
        return full_sql

    @staticmethod
    def all_minimal():
        """Get all datalab data in the minimal style."""
        results = DatalabData.filter_minimal(None, None, None)
        return results

    @staticmethod
    def combos_indicator(indicator):
        """Get all valid combos of survey and characteristic group.

        Args:
            indicator_code (str): An indicator code

        Returns:
            A dictionary with two key names and list values.
        """
        select_args = (Survey.code, DatalabData.char_grp1.code)
        joined = DatalabData.all_joined(*select_args)
        filtered = joined.filter(Indicator.code == indicator)
        results = filtered.distinct().all()
        survey_codes = set()
        char_grp_codes = set()
        for item in results:
            survey_code = item[0]
            survey_codes.add(survey_code)
            char_grp_code = item[1]
            char_grp_codes.add(char_grp_code)
        to_return = {
            'survey.id': sorted(list(survey_codes)),
            'characteristicGroup.id': sorted(list(char_grp_codes))
        }
        return to_return

    @staticmethod
    def combos_char_grp(char_grp_code):
        """Get all valid combos of survey and indicator.

        Args:
            char_grp_code (str): A characteristic group code

        Returns:
            A dictionary with two key names and list values.
        """
        select_args = (Survey.code, Indicator.code)
        joined = DatalabData.all_joined(*select_args)
        filtered = joined.filter(DatalabData.char_grp1.code == char_grp_code)
        results = filtered.distinct().all()
        survey_codes = set()
        indicator_codes = set()
        for item in results:
            survey_code = item[0]
            survey_codes.add(survey_code)
            indicator_code = item[1]
            indicator_codes.add(indicator_code)
        to_return = {
            'survey.id': sorted(list(survey_codes)),
            'indicator.id': sorted(list(indicator_codes))
        }
        return to_return

    @staticmethod
    def combos_survey_list(survey_list):
        # TODO (jkp 2017-08-29): make better. make hashmaps one to the other
        """Get all valid combos of indicator and characteristic groups.

        Args:
            survey_list (str): A list of survey codes, comma separated

        Returns:
            An object.
        """
        select_args = (Indicator.code, DatalabData.char_grp1.code)
        joined = DatalabData.all_joined(*select_args)
        survey_list_sql = DatalabData.survey_list_to_sql(survey_list)
        filtered = joined.filter(survey_list_sql)
        results = filtered.distinct().all()
        indicator_dict = {}
        char_grp_dict = {}
        for item in results:
            this_indicator = item[0]
            this_char_grp = item[1]
            if this_indicator in indicator_dict:
                indicator_dict[this_indicator].add(this_char_grp)
            else:
                indicator_dict[this_indicator] = set([this_char_grp])
            if this_char_grp in char_grp_dict:
                char_grp_dict[this_char_grp].add(this_indicator)
            else:
                char_grp_dict[this_char_grp] = set([this_indicator])
        new_indicator_dict = {
            k: sorted(list(v)) for k, v in indicator_dict.items()
        }
        new_char_grp_dict = {
            k: sorted(list(v)) for k, v in char_grp_dict.items()
        }
        to_return = {
            'indicators': new_indicator_dict,
            'characteristicGroups': new_char_grp_dict
        }
        return to_return

    @staticmethod
    def combos_indicator_char_grp(indicator_code, char_grp_code):
        """Get all valid surveys from supplied arguments.

        Args:
            indicator_code (str): An indicator code
            char_grp_code (str): A characteristic group code

        Returns:
            A list of surveys that have data for the supplied indicator and
            characteristic group
        """
        select_arg = Survey.code
        joined = DatalabData.all_joined(select_arg)
        filtered = joined.filter(Indicator.code == indicator_code) \
            .filter(DatalabData.char_grp1.code == char_grp_code)
        results = filtered.distinct().all()
        to_return = {
            'survey.id': [item[0] for item in results]
        }
        return to_return

    @staticmethod
    def init_indicators():
        """Datalab init."""
        select_args = Indicator
        joined = DatalabData.all_joined(select_args)
        results = joined.distinct().all()
        indicator_categories = []
        for ind in results:
            for cat in indicator_categories:
                if ind.level2.code == cat['category.label.id']:
                    cat['indicators'].append(ind.datalab_init_json())
                    break
            else:
                indicator_categories.append({
                    'category.label.id': ind.level2.code,
                    'indicators': [ind.datalab_init_json()]
                })
        return indicator_categories

    @staticmethod
    def init_char_grp():
        """Datalab init."""
        select_args = DatalabData.char_grp1
        joined = DatalabData.all_joined(select_args)
        results = joined.distinct().all()
        chargrp_categories = []
        for char_grp in results:
            for cat in chargrp_categories:
                if char_grp.category.code == cat['category.label.id']:
                    cat['characteristicGroups'].append(char_grp.
                                                       datalab_init_json())
                    break
            else:
                chargrp_categories.append({
                    'category.label.id': char_grp.category.code,
                    'characteristicGroups': [char_grp.datalab_init_json()]
                })

        return chargrp_categories

    @staticmethod
    def init_chars():
        """Datalab init."""
        select_args = DatalabData.char1
        joined = DatalabData.all_joined(select_args)
        results = joined.distinct().all()
        results = [record.datalab_init_json() if record is not None else "none"
                   for record in results]
        return results

    @staticmethod
    def init_surveys():
        """Datalab init."""
        select_args = Survey
        joined = DatalabData.all_joined(select_args)
        results = joined.distinct().all()

        country_order = []
        country_map = {}
        country_geo_map = {}
        for survey in results:
            country = survey.country
            country_code = country.code
            geo = survey.geography
            geo_code = geo.code
            country_geo_key = '|'.join((country_code, geo_code))
            if not country in country_order:
                country_order.append(country)

            if country_code in country_map and geo not in country_map[country_code]:
                country_map[country_code].append(geo)
            elif country_code not in country_map:
                country_map[country_code] = [geo]

            if country_geo_key in country_geo_map:
                country_geo_map[country_geo_key].append(survey)
            else:
                country_geo_map[country_geo_key] = [survey]

        survey_country_list = []
        for country in country_order:
            this_country_geos = country_map[country.code]
            geography_list = []
            for geo in this_country_geos:
                country_geo_key = '|'.join((country.code, geo.code))
                surveys = country_geo_map[country_geo_key]
                survey_list = [s.datalab_init_json() for s in surveys]
                this_geo_obj = {
                    'geography.label.id': geo.subheading.code,
                    'surveys': survey_list
                }
                geography_list.append(this_geo_obj)
            this_country_obj = {
                'country.label.id': country.label.code,
                'geographies': geography_list
            }
            survey_country_list.append(this_country_obj)

        return survey_country_list

    # TODO: (jkp 2017-08-29) Get other languages. Needs: Nothing.
    @staticmethod
    def init_strings():
        """Datalab init."""
        results = EnglishString.query.all()
        results = [record.datalab_init_json() for record in results]
        results = dict(ChainMap(*results))
        return results

    @staticmethod
    def init_languages():
        """Datalab init."""
        return Translation.languages()

    @staticmethod
    def datalab_init():
        """Datalab Init."""
        return {
            'indicatorCategories': DatalabData.init_indicators(),
            'characteristicGroupCategories': DatalabData.init_char_grp(),
            'characteristics': DatalabData.init_chars(),
            'surveyCountries': DatalabData.init_surveys(),
            'strings': DatalabData.init_strings(),
            'languages': DatalabData.init_languages()
        }

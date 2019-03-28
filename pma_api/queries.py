"""Queries."""
from collections import ChainMap
from typing import Dict, List

from sqlalchemy import or_
from sqlalchemy.orm import aliased

from . import db
from .models import (Characteristic, CharacteristicGroup, Country, Data,
                     EnglishString, Geography, Indicator, Survey, Translation)


# pylint: disable=too-many-public-methods
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
            .join(Geography, Survey.geography_id == Geography.id) \
            .join(Country, Survey.country_id == Country.id) \
            .join(Indicator, Data.indicator_id == Indicator.id) \
            .outerjoin(chr1, Data.char1_id == chr1.id) \
            .outerjoin(grp1, grp1.id == chr1.char_grp_id) \
            .outerjoin(chr2, Data.char2_id == chr2.id) \
            .outerjoin(grp2, grp2.id == chr2.char_grp_id)
        return joined

    @staticmethod
    def series_query(survey_codes, indicator_code, char_grp_code, over_time):
        """Get the series based on supplied codes."""
        json_list: List[Dict] = DatalabData.filter_minimal(
            survey_codes, indicator_code, char_grp_code, over_time)
        if over_time:
            series_list = DatalabData.data_to_time_series(json_list)
        else:
            series_list = DatalabData.data_to_series(json_list)
        return series_list

    @staticmethod
    def data_to_time_series(sorted_data):
        """Transform a sorted list of data into time series."""
        curr_char = None
        curr_geo = None
        results = []
        next_series = {}
        for obj in sorted_data:
            new_char = obj['characteristic.id'] != curr_char
            new_geo = obj['geography.id'] != curr_geo
            if new_char or new_geo:
                if curr_char and curr_geo:
                    results.append(next_series)
                next_series = {
                    'characteristic.id': obj.pop('characteristic.id'),
                    'characteristic.label.id':
                        obj.pop('characteristic.label.id'),
                    'geography.id': obj.pop('geography.id'),
                    'geography.label.id': obj.pop('geography.label.id'),
                    'country.id': obj.pop('country.id'),
                    'country.label.id': obj.pop('country.label.id'),
                    'values': [
                        {
                            'survey.id': obj.pop('survey.id'),
                            'survey.label.id': obj.pop('survey.label.id'),
                            'survey.date': obj.pop('survey.date'),
                            'value': obj.pop('value'),
                        }
                    ]
                }
                curr_char = next_series['characteristic.id']
                curr_geo = next_series['geography.id']
            else:
                next_series['values'].append({
                    'survey.id': obj.pop('survey.id'),
                    'survey.label.id': obj.pop('survey.label.id'),
                    'survey.date': obj.pop('survey.date'),
                    'value': obj.pop('value'),
                })
        if next_series:
            results.append(next_series)
        return results

    @staticmethod
    def data_to_series(sorted_data):
        """Transform a sorted list of data into series."""
        curr_survey = None
        results = []
        next_series = {}
        for obj in sorted_data:
            if obj['survey.id'] != curr_survey:
                if curr_survey:
                    results.append(next_series)
                next_series = {
                    'survey.id': obj.pop('survey.id'),
                    'survey.label.id': obj.pop('survey.label.id'),
                    'geography.id': obj.pop('geography.id'),
                    'geography.label.id': obj.pop('geography.label.id'),
                    'country.id': obj.pop('country.id'),
                    'country.label.id': obj.pop('country.label.id'),
                    'values': [
                        {
                            'characteristic.label.id':
                                obj.pop('characteristic.label.id'),
                            'characteristic.id': obj.pop('characteristic.id'),
                            'value': obj.pop('value'),
                        }
                    ]
                }
                curr_survey = next_series['survey.id']
            else:
                next_series['values'].append({
                    'characteristic.label.id':
                        obj.pop('characteristic.label.id'),
                    'characteristic.id': obj.pop('characteristic.id'),
                    'value': obj.pop('value'),
                })
        if next_series:
            results.append(next_series)
        return results

    @staticmethod
    def filter_readable(survey_codes, indicator_code, char_grp_code,
                        lang=None):
        """Get filtered Datalab data and return readable columns.

        Args:
            survey_codes (str): Comma-delimited list of survey codes
            indicator_code (str): An indicator code
            char_grp_code (str): A characteristic group code
            lang (str): The language, if specified.

        Filters the data based on the function arguments.

        Returns:
            A list of simple python objects, one for each record found by
            applying the various filters.
        """
        chr1 = DatalabData.char1
        grp1, grp2 = DatalabData.char_grp1, DatalabData.char_grp2
        select_args = (Data, Survey, Indicator, grp1, chr1)
        filtered = DatalabData.all_joined(*select_args)
        if survey_codes:
            survey_sql = DatalabData.survey_list_to_sql(survey_codes)
            filtered = filtered.filter(survey_sql)
        if indicator_code:
            filtered = filtered.filter(Indicator.code == indicator_code)
        if char_grp_code:
            filtered = filtered.filter(grp1.code == char_grp_code)
        # TODO (jkp, begin=2017-08-28): This will be grp2.code is None
        # eventually when the Data show "none" for char_grp2 in excel import
        # Remove E711 from .pycodestyle
        # pylint: disable=singleton-comparison
        filtered = filtered.filter(grp2.code is None)
        results = filtered.all()
        json_results = []
        for item in results:
            precision = item[0].precision
            if precision is None:
                precision = 1
            value = round(item[0].value, precision)
            this_dict = {
                'value': value,
                'survey.id': item[1].code,
                'survey.date': item[1].start_date.strftime('%m-%Y'),
                'indicator.label': item[2].label.to_string(lang),
                'characteristicGroup.label': item[3].label.to_string(lang),
                'characteristic.label': item[4].label.to_string(lang)
            }
            json_results.append(this_dict)
        return json_results

    @staticmethod
    def filter_minimal(survey_codes: str, indicator_code: str,
                       char_grp_code: str, over_time) -> List[Dict]:
        """Get filtered Datalab data and return minimal columns.

        Args:
            survey_codes (str): Comma-delimited list of survey codes
            indicator_code (str): An indicator code
            char_grp_code (str): A characteristic group code
            over_time (bool): Filter charting over time?

        Filters the data based on the function arguments. The returned data
        are data value, the precision, the survey code, the indicator code,
        the characteristic group code, and the characteristic code.

        Returns:
            A list of simple python objects, one for each record found by
            applying the various filters.
        """
        chr1 = DatalabData.char1
        grp1, grp2 = DatalabData.char_grp1, DatalabData.char_grp2
        select_args = (Data, Survey, Indicator.code, grp1.code, chr1,
                       Geography, Country)
        filtered = DatalabData.all_joined(*select_args)
        if survey_codes:
            survey_sql = DatalabData.survey_list_to_sql(survey_codes)
            filtered = filtered.filter(survey_sql)
        if indicator_code:
            filtered = filtered.filter(Indicator.code == indicator_code)
        if char_grp_code:
            filtered = filtered.filter(grp1.code == char_grp_code)
        # TODO (jkp, begin=2017-08-28): This will be grp2.code == 'none'
        # eventually when the Data show "none" for char_grp2 in excel import
        # Remove E711 from .pycodestyle
        # pylint: disable=singleton-comparison
        filtered = filtered.filter(grp2.code is None)
        if over_time:
            # This ordering is very important!
            ordered = filtered.order_by(Geography.order) \
                              .order_by(chr1.order) \
                              .order_by(Survey.order)
            # Perhaps order by the date of the survey?
        else:
            ordered = filtered.order_by(Survey.order) \
                              .order_by(chr1.order)
        results = ordered.all()
        json_results = []

        for item in results:
            this_dict = {
                'value': item[0].value,
                'precision': item[0].precision,
                'survey.id': item[1].code,
                'survey.date': item[1].start_date.strftime('%m-%Y'),
                'survey.label.id': item[1].label.code,
                'indicator.id': item[2],
                'characteristicGroup.id': item[3],
                'characteristic.id': item[4].code,
                'characteristic.label.id': item[4].label.code,
                'geography.label.id': item[5].subheading.code,
                'geography.id': item[5].code,
                'country.label.id': item[6].label.code,
                'country.id': item[6].code
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

    # pylint: disable=too-many-locals
    @staticmethod
    def combos_all(survey_list: List[str], indicator: str, char_grp: str):
        """Get lists of all valid datalab selections.

        Based on a current selection in the datalab, this method returns lists
        of what should be clickable in each of the three selection areas of
        the datalab.

        Args:
            survey_list (list(str)): A list of survey codes. An empty list if
            not provided.
            indicator (str): An indicator code or None if not provided.
            char_grp(str): An characteristic group code or None if not
            provided.

        Returns:
            A dictionary with a survey list, an indicator list, and a
            characteristic group list.
        """
        def keep_survey(this_indicator: str, this_char_grp: str):
            """Determine whether a survey from the data is valid.

            Args:
                this_indicator (str): An indicator code from the data
                this_char_grp (str): A characteristic code from the data

            Returns:
                True or False to say if the related survey code should be
                included in the return set.
            """
            if not indicator and not char_grp:
                keep = True
            elif not indicator and not char_grp:
                keep = this_char_grp == char_grp
            elif not indicator and not char_grp:
                keep = this_indicator == indicator
            else:
                indicator_match = this_indicator == indicator
                char_grp_match = this_char_grp == char_grp
                keep = indicator_match and char_grp_match
            return keep

        def keep_indicator(this_survey, this_char_grp):
            """Determine whether an indicator from the data is valid.

            Args:
                this_survey (str): A survey code from the data
                this_char_grp (str): A characteristic code from the data

            Returns:
                True or False to say if the related indicator code should be
                included in the return set.
            """
            if not survey_list and char_grp is None:
                keep = True
            elif not survey_list and char_grp is not None:
                keep = this_char_grp == char_grp
            elif survey_list and char_grp is None:
                keep = this_survey in survey_list
            else:
                survey_match = this_survey in survey_list
                char_grp_match = this_char_grp == char_grp
                keep = survey_match and char_grp_match
            return keep

        def keep_char_grp(this_survey, this_indicator):
            """Determine whether a characterist group from the data is valid.

            Args:
                this_survey (str): A survey code from the data
                this_indicator (str): An indicator code from the data

            Returns:
                True or False to say if the related characteristic group code
                should be included in the return set.
            """
            if not survey_list and indicator is None:
                keep = True
            elif not survey_list and indicator is not None:
                keep = this_indicator == indicator
            elif survey_list and indicator is None:
                keep = this_survey in survey_list
            else:
                survey_match = this_survey in survey_list
                indicator_match = this_indicator == indicator
                keep = survey_match and indicator_match
            return keep

        select_args = (Survey.code, Indicator.code, DatalabData.char_grp1.code)
        joined = DatalabData.all_joined(*select_args)
        results = joined.distinct().all()
        surveys = set()
        indicators = set()
        char_grps = set()
        for survey_code, indicator_code, char_grp_code in results:
            if keep_survey(indicator_code, char_grp_code):
                surveys.add(survey_code)
            if keep_indicator(survey_code, char_grp_code):
                indicators.add(indicator_code)
            if keep_char_grp(survey_code, indicator_code):
                char_grps.add(char_grp_code)
        json_obj = {
            'survey.id': sorted(list(surveys)),
            'indicator.id': sorted(list(indicators)),
            'characteristicGroup.id': sorted(list(char_grps))
        }
        return json_obj

    @staticmethod
    def all_minimal() -> List[Dict]:
        """Get all datalab data in the minimal style.

        Returns:
            list(dict): Datalab data, filtered minimally
        """
        results: List[Dict] = DatalabData.filter_minimal('', '', '', False)

        return results

    @staticmethod
    def combos_indicator(indicator: str) -> Dict:
        """Get all valid combos of survey and characteristic group.

        Args:
            indicator (str): An indicator code

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
                indicator_dict[this_indicator] = {this_char_grp}
            if this_char_grp in char_grp_dict:
                char_grp_dict[this_char_grp].add(this_indicator)
            else:
                char_grp_dict[this_char_grp] = {this_indicator}
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
        ordered = joined.order_by(Indicator.order)
        results = ordered.distinct().all()
        indicator_categories = []
        for ind in results:
            for cat in indicator_categories:
                if ind.level2.code == cat['label.id']:
                    cat['indicators'].append(ind.datalab_init_json())
                    break
            else:
                indicator_categories.append({
                    'label.id': ind.level2.code,
                    'indicators': [ind.datalab_init_json()]
                })
        return indicator_categories

    @staticmethod
    def init_char_grp():
        """Datalab init."""
        select_args = DatalabData.char_grp1
        joined = DatalabData.all_joined(select_args)
        ordered = joined.order_by(DatalabData.char_grp1.order)
        results = ordered.distinct().all()
        chargrp_categories = []
        for char_grp in results:
            for cat in chargrp_categories:
                if char_grp.category.code == cat['label.id']:
                    cat['characteristicGroups'].append(char_grp.
                                                       datalab_init_json())
                    break
            else:
                chargrp_categories.append({
                    'label.id': char_grp.category.code,
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
        # pylint: disable=too-many-locals
        # TODO (2017-09-05 jkp) refactor so that this method is simpler
        """Datalab init."""
        select_args = Survey
        joined = DatalabData.all_joined(select_args)
        ordered = joined.order_by(Country.order) \
                        .order_by(Geography.order) \
                        .order_by(Survey.order)
        results = ordered.distinct().all()

        country_order = []
        country_map = {}
        country_geo_map = {}
        for survey in results:
            country = survey.country
            country_code = country.code
            geo = survey.geography
            geo_code = geo.code
            country_geo_key = '|'.join((country_code, geo_code))
            if country not in country_order:
                country_order.append(country)

            if country_code in country_map:
                if geo not in country_map[country_code]:
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
                    'label.id': geo.subheading.code,
                    'surveys': survey_list
                }
                geography_list.append(this_geo_obj)
            this_country_obj = {
                'label.id': country.label.code,
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

    @staticmethod
    def query_input(survey: str, indicator: str, char_grp: str) -> Dict:
        """Build up a dictionary of query input to return with API result.

        Args:
            survey (str): Comma-delimited list of survey codes
            indicator (str): An indicator code
            char_grp (str): A characteristic group code

        Returns:
            A dictionary with lists of input data. Data is from datalab init.
        """
        survey_list = sorted(survey.split(',')) if survey else []
        survey_records = Survey.get_by_code(survey_list) if survey_list else []
        input_survey = \
            [r.datalab_init_json(reduced=False) for r in survey_records]
        indicator_records = Indicator.get_by_code(indicator)

        if indicator_records:
            input_indicator = [indicator_records[0].datalab_init_json()]
        else:
            input_indicator = None
        char_grp_records = CharacteristicGroup.get_by_code(char_grp)
        if char_grp_records:
            input_char_grp = [char_grp_records[0].datalab_init_json()]
        else:
            input_char_grp = None

        query_input = {
            'surveys': input_survey,
            'characteristicGroups': input_char_grp,
            'indicators': input_indicator
        }

        return query_input

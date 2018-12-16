"""Core models."""
from flask import url_for

from . import db
from .api_base import ApiModel
from pma_api.utils import next64
from copy import copy


class Indicator(ApiModel):
    """Indicator model."""

    __tablename__ = 'indicator'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'),
                         nullable=False)
    order = db.Column(db.Integer, unique=True)
    type = db.Column(db.String)
    definition_id = db.Column(db.Integer, db.ForeignKey('english_string.id'),
                              nullable=False)
    level1_id = db.Column(db.Integer, db.ForeignKey('english_string.id'),
                          nullable=False)
    level2_id = db.Column(db.Integer, db.ForeignKey('english_string.id'),
                          nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey('english_string.id'),
                          nullable=False)
    # TODO: (jkp 2017-08-29) Should this be a translated string?
    # Needs: Nothing?
    denominator = db.Column(db.String)
    measurement_type = db.Column(db.String)
    is_favorite = db.Column(db.Boolean)
    favorite_order = db.Column(db.Integer, unique=True)

    label = db.relationship('EnglishString', foreign_keys=label_id)
    definition = db.relationship('EnglishString', foreign_keys=definition_id)
    level1 = db.relationship('EnglishString', foreign_keys=level1_id)
    level2 = db.relationship('EnglishString', foreign_keys=level2_id)
    domain = db.relationship('EnglishString', foreign_keys=domain_id)

    def __init__(self, **kwargs):
        """Initialize instance of model.

        Does a few things: (1) Updates instance based on mapping from API query
        parameter names to model field names, (2) Reformats any empty strings,
        and (3) Calls super init.
        """
        kwargs['is_favorite'] = bool(kwargs['is_favorite'])
        self.update_kwargs_english(kwargs, 'level1', 'level1_id')
        self.update_kwargs_english(kwargs, 'level2', 'level2_id')
        self.update_kwargs_english(kwargs, 'domain', 'domain_id')
        self.update_kwargs_english(kwargs, 'definition', 'definition_id')
        self.update_kwargs_english(kwargs, 'label', 'label_id')
        super(Indicator, self).__init__(**kwargs)

    def full_json(self, lang=None, jns=False, endpoint=None):
        """Return dictionary ready to convert to JSON as response.

        This response contains fields of 1 or more related
        model(s) which are included along with fields for this model.

        Args:
            lang (str): The language, if specified.
            jns (bool): If true, namespaces all dictionary keys with prefixed
            table name, e.g. indicator.id.
            endpoint (str): If supplied, provides URL for entity in response.

        Returns:
            dict: API response ready to be JSONified.
        """
        result = {
            'id': self.code,
            'order': self.order,
            'type': self.type,
            'denominator': self.denominator,
            'measurementType': self.measurement_type,
            'isFavorite': self.is_favorite,
            'favoriteOrder': self.favorite_order
        }

        label_str = self.label.to_string(lang)
        defn_str = self.definition.to_string(lang)
        level1_str = self.level1.to_string(lang)
        level2_str = self.level2.to_string(lang)
        domain_str = self.domain.to_string(lang)

        result['label'] = label_str
        result['definition'] = defn_str
        result['level1'] = level1_str
        result['level2'] = level2_str
        result['domain'] = domain_str

        if endpoint is not None:
            result['url'] = url_for(endpoint, code=self.code, _external=True)

        if jns:
            result = self.namespace(result, 'indicator')

        return result

    def __repr__(self):
        """Return a representation of this object."""
        return '<Indicator "{}">'.format(self.code)

    def datalab_init_json(self):
        """Datalab init json: Indicator."""
        to_return = {
            'id': self.code,
            'label.id': self.label.code,
            'definition.id': self.definition.code,
            'type': self.type
        }
        return to_return


class CharacteristicGroup(ApiModel):
    """CharacteristicGroup model."""

    __tablename__ = 'characteristic_group'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    definition_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    order = db.Column(db.Integer, unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))

    label = db.relationship('EnglishString', foreign_keys=label_id)
    definition = db.relationship('EnglishString', foreign_keys=definition_id)
    category = db.relationship('EnglishString', foreign_keys=category_id)

    def __init__(self, **kwargs):
        """Initialize instance of model.

        Does a few things: (1) Removes unnecessary fields, (2) Converts API
        query parameters to model field name equivalents, (3) Inserts new
        values into the EnglishString translation table if not present, and
        (4) calls super init.
        """
        self.update_kwargs_english(kwargs, 'label', 'label_id')
        self.update_kwargs_english(kwargs, 'definition', 'definition_id')
        self.update_kwargs_english(kwargs, 'category', 'category_id')
        super(CharacteristicGroup, self).__init__(**kwargs)

    def full_json(self, lang=None, jns=False, index=None):
        """Return dictionary ready to convert to JSON as response.

        Args:
            lang (str): The language, if specified.
            jns (bool): If true, namespaces all dictionary keys with prefixed
            table name.
            index (int): Field index for fields that have multiple instances of
            itself, e.g. "characteristic1", "characteristic2".

        Returns:
            dict: API response ready to be JSONified.
        """
        result = {
            'id': self.code,
            'label': self.label.to_string(lang),
            'definition': self.definition.to_string(lang)
        }
        if jns:
            result = self.namespace(result, 'charGrp', index=index)
        return result

    def __repr__(self):
        """Return a representation of this object."""
        return '<CharacteristicGroup "{}">'.format(self.code)

    @staticmethod
    def none_json(jns=False, index=None):
        """Return dictionary ready to convert to JSON as response.

        All values in this dictionary are set to none, serving the cases where
        no data is found or needs to be supplied.

        Args:
            jns (bool): If true, namespaces all dictionary keys with prefixed
            table name.
            index (int): Field index for fields that have multiple instances of
            itself, e.g. "characteristic1", "characteristic2".

        Returns:
            dict: API response ready to be JSONified.
        """
        result = {
            'id': None,
            'label': None,
            'definition': None
        }
        if jns:
            result = ApiModel.namespace(result, 'charGrp', index=index)
        return result

    def datalab_init_json(self):
        """Datalab init json: CharacteristicGroup."""
        to_return = {
            'id': self.code,
            'label.id': self.label.code,
            'definition.id': self.definition.code,
        }
        return to_return


class Characteristic(ApiModel):
    """Characteristic model."""

    __tablename__ = 'characteristic'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    order = db.Column(db.Integer, unique=True)
    char_grp_id = \
        db.Column(db.Integer, db.ForeignKey('characteristic_group.id'))

    char_grp = db.relationship('CharacteristicGroup')
    label = db.relationship('EnglishString', foreign_keys=label_id)

    def __init__(self, **kwargs):
        """Initialize instance of model.

        Does a few things: (1) Removes unnecessary fields, (2) Converts API
        query parameters to model field name equivalents, (3) Inserts new
        values into the EnglishString translation table if not present, and
        (4) calls super init.

        Raises:
            AttributeError: If valid ID is not found for CharacteristicGroup.
        """
        self.update_kwargs_english(kwargs, 'label', 'label_id')
        self.set_kwargs_id(kwargs, 'char_grp_code', 'char_grp_id',
                           CharacteristicGroup)
        super(Characteristic, self).__init__(**kwargs)

    def full_json(self, lang=None, jns=False, index=None):
        """Return dictionary ready to convert to JSON as response.

        This response contains fields of 1 or more related
        model(s) which are included along with fields for this model.

        Args:
            lang (str): The language, if specified.
            jns (bool): If true, namespaces all dictionary keys with prefixed
            table name.
            index (int): Field index for fields that have multiple instances of
            itself, e.g. "characteristic1", "characteristic2".

        Returns:
            dict: API response ready to be JSONified.
        """
        result = {
            'id': self.code,
            'order': self.order
        }
        result['label'] = self.label.to_string(lang)

        if jns:
            result = self.namespace(result, 'char', index=index)

        char_grp_json = \
            self.char_grp.full_json(lang=lang, jns=True, index=index)

        result.update(char_grp_json)
        return result

    def __repr__(self):
        """Return a representation of this object."""
        return '<Characteristic "{}">'.format(self.code)

    def datalab_init_json(self):
        """Datalab init json: Characteristic."""
        to_return = {
            'id': self.code,
            'label.id': self.label.code,
            'order': self.order,
        }
        return to_return

    @staticmethod
    def none_json(jns=False, index=None):
        """Return dictionary ready to convert to JSON as response.

        All values in this dictionary are set to none, serving the cases where
        no data is found or needs to be supplied.

        This response contains fields of 1 or more related
        model(s) which are included along with fields for this model.

        Args:
            jns (bool): If true, namespaces all dictionary keys with prefixed
            table name.
            index (int): Field index for fields that have multiple instances of
            itself, e.g. "characteristic1", "characteristic2".

        Returns:
            dict: API response ready to be JSONified.
        """
        result = {
            'id': None,
            'order': None,
            'label': None,
        }
        if jns:
            result = ApiModel.namespace(result, 'char', index=index)
        char_grp_json = \
            CharacteristicGroup.none_json(jns=True, index=index)
        result.update(char_grp_json)
        return result


class Data(ApiModel):
    """Data model."""

    __tablename__ = 'datum'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True)
    value = db.Column(db.Float, nullable=False)
    lower_ci = db.Column(db.Float)
    upper_ci = db.Column(db.Float)
    level_ci = db.Column(db.Float)
    precision = db.Column(db.Integer)
    is_total = db.Column(db.Boolean)
    denom_w = db.Column(db.Float)
    denom_uw = db.Column(db.Float)

    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'))
    indicator_id = db.Column(db.Integer, db.ForeignKey('indicator.id'))
    char1_id = db.Column(db.Integer, db.ForeignKey('characteristic.id'))
    char2_id = db.Column(db.Integer, db.ForeignKey('characteristic.id'))
    geo_id = db.Column(db.Integer, db.ForeignKey('geography.id'))

    survey = db.relationship('Survey', foreign_keys=survey_id)
    indicator = db.relationship('Indicator', foreign_keys=indicator_id)
    char1 = db.relationship('Characteristic', foreign_keys=char1_id)
    char2 = db.relationship('Characteristic', foreign_keys=char2_id)
    geo = db.relationship('Geography', foreign_keys=geo_id)

    def __init__(self, **kwargs):
        """Initialize instance of model.

        Does a few things: (1) Updates instance based on mapping from API query
        parameter names to model field names, (2) Reformats any empty strings,
        (3) Sets a randomly generated code string, and (4) Calls super init.
        """
        kwargs_copy = copy(kwargs)
        if kwargs:
            kwargs['is_total'] = bool(kwargs['is_total'])
            self.set_kwargs_id(kwargs, 'survey_code', 'survey_id', Survey)
            try:
                self.set_kwargs_id(kwargs, 'indicator_code', 'indicator_id',
                                   Indicator)
                self.set_kwargs_id(kwargs, 'char1_code', 'char1_id',
                                   Characteristic, False)
                self.set_kwargs_id(kwargs, 'char2_code', 'char2_id',
                                   Characteristic, False)
                self.empty_to_none(kwargs)
            except KeyError as err:
                msg = """
                {}

                Error occured while trying to store the following data:
                {}
                """.format(str(err),
                           ', '.join(['{}: {}'.format(k, v)
                                      for k, v in kwargs_copy.items()]))
                raise KeyError(msg)
            kwargs['code'] = next64()
            super(Data, self).__init__(**kwargs)

    def full_json(self, lang=None, jns=False):
        """Return dictionary ready to convert to JSON as response.

        This response contains fields of 1 or more related
        model(s) which are included along with fields for this model.

        Args:
            lang (str): The language, if specified.
            jns (bool): If true, namespaces all dictionary keys with prefixed
            table name.

        Returns:
            dict: API response ready to be JSONified.
        """
        result = {
            'id': self.code,
            'value': self.value,
            'lowerCi': self.lower_ci,
            'upperCi': self.upper_ci,
            'levelCi': self.level_ci,
            'precision': self.precision,
            'isTotal': self.is_total,
            'denominatorWeighted': self.denom_w,
            'denominatorUnweighted': self.denom_uw,
        }

        if jns:
            result = self.namespace(result, 'data')

        survey_json = self.survey.full_json(lang=lang, jns=True)
        indicator_json = self.indicator.full_json(lang=lang, jns=True)
        if self.char1 is not None:
            char1_json = self.char1.full_json(lang, jns=True, index=1)
        else:
            char1_json = Characteristic.none_json(jns=True, index=1)
        if self.char2 is not None:
            char2_json = self.char2.full_json(lang, jns=True, index=2)
        else:
            char2_json = Characteristic.none_json(jns=True, index=2)
        if self.geo is not None:
            geo_json = self.geo.full_json(lang, jns=True)
        else:
            geo_json = Geography.none_json(jns=True)

        result.update(survey_json)
        result.update(indicator_json)
        result.update(char1_json)
        result.update(char2_json)
        result.update(geo_json)

        return result

    def __repr__(self):
        """Return a representation of this object."""
        return '<Data "{}">'.format(self.code)


class Survey(ApiModel):
    """Survey model."""

    __tablename__ = 'survey'
    id = db.Column(db.Integer, primary_key=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'),
                         nullable=False)
    order = db.Column(db.Integer, unique=True)
    type = db.Column(db.String)
    year = db.Column(db.Integer)
    round = db.Column(db.Integer)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    code = db.Column(db.String, unique=True)
    pma_code = db.Column(db.String)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'))
    geography_id = db.Column(db.Integer, db.ForeignKey('geography.id'))
    partner_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))

    label = db.relationship('EnglishString', foreign_keys=label_id)
    country = db.relationship('Country')
    geography = db.relationship('Geography')
    partner = db.relationship('EnglishString', foreign_keys=partner_id)

    def url_for(self):
        """Supply URL for resource entity.

        Returns:
            dict: Dict of key 'url' and value of URL for resource entity.
        """
        return {'url': url_for('api.get_survey', code=self.pma_code,
                               _external=True)}

    def full_json(self, lang=None, jns=False):
        """Return dictionary ready to convert to JSON as response.

        This response contains fields of 1 or more related
        model(s) which are included along with fields for this model.

        Args:
            lang (str): The language, if specified.
            jns (bool): If true, namespaces all dictionary keys with prefixed
            table name.

        Returns:
            dict: API response ready to be JSONified.
        """
        result = {
            'order': self.order,
            'type': self.type,
            'year': self.year,
            'round': self.round,
            'start_date': self.start_date.date().isoformat(),
            'end_date': self.end_date.date().isoformat(),
            'id': self.code,
            'pma_code': self.pma_code,
        }

        if jns:
            result = self.namespace(result, 'survey')

        country_json = self.country.full_json(lang=lang, jns=True)

        result.update(country_json)
        return result

    def datalab_init_json(self, reduced=True):
        """Datalab init json: Survey."""
        to_return = {
            'id': self.code,
            'partner.label.id': self.partner.code,
            'label.id': self.label.code,
        }
        if not reduced:
            to_return.update({
                'geography.label.id': self.geography.subheading.code,
                'country.label.id': self.country.label.code
            })
        return to_return

    def __init__(self, **kwargs):
        """Initialize instance of model.

        Does a few things: (1) Removes unnecessary fields, (2) Converts API
        query parameters to model field name equivalents, (3) Inserts new
        values into the EnglishString translation table if not present, and
        (4) calls super init.

        Raises:
            AttributeError: If valid ID is not found for Country.
        """
        self.update_kwargs_english(kwargs, 'label', 'label_id')
        self.update_kwargs_english(kwargs, 'partner', 'partner_id')
        self.update_kwargs_date(kwargs, 'start_date', '%m-%Y')
        self.update_kwargs_date(kwargs, 'end_date', '%m-%Y')
        self.set_kwargs_id(kwargs, 'country_code', 'country_id', Country,
                           required=True)
        self.set_kwargs_id(kwargs, 'geography_code', 'geography_id', Geography,
                           required=False)
        super(Survey, self).__init__(**kwargs)

    def __repr__(self):
        """Return a representation of this object."""
        return '<Survey "{}">'.format(self.code)


class Country(ApiModel):
    """Country model."""

    __tablename__ = 'country'
    id = db.Column(db.Integer, primary_key=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    order = db.Column(db.Integer, unique=True)
    subregion = db.Column(db.String)
    region = db.Column(db.String)
    code = db.Column(db.String, unique=True)

    label = db.relationship('EnglishString', foreign_keys=label_id)

    api_schema = {  # size_min & size_max currently unused.
        'fields': {
            'id': {
                'restrictions': {
                    'type': str,
                    'size_min': 1,
                    'size_max': None,
                    'queryable': True
                },
            },
            'label': {
                'restrictions': {
                    'type': str,
                    'size_min': 1,
                    'size_max': None,
                    'queryable': True
                }

            },
            'order': {
                'restrictions': {
                    'type': int,
                    'size_min': 1,
                    'size_max': None,
                    'queryable': False
                }

            },
            'region': {
                'restrictions': {
                    'type': str,
                    'size_min': 1,
                    'size_max': None,
                    'queryable': True
                }

            },
            'subregion': {
                'restrictions': {
                    'type': str,
                    'size_min': 1,
                    'size_max': None,
                    'queryable': True
                }

            }
        }
    }

    # def __init__(self, label_id, order, ):
    def __init__(self, **kwargs):
        """Initialize instance of model.

        Does a few things: (1) Updates instance based on mapping from API query
        parameter names to model field names, and (2) calls super init.

        Example Usage:
            new_country = Country(
                label_id='Burkina Faso',
                order='1',
                subregion='West Africa',
                region='Africa',
                code='BF'
            )
        """
        self.update_kwargs_english(kwargs, 'label', 'label_id')
        super(Country, self).__init__(**kwargs)

    @staticmethod
    def validate_param_types(request_args):
        """Validate query parameter types.

        Args:
            request_args (ImmutableMultiDict): API query parameters.

        Returns
            bool: True if valid param types, else false.
        """
        # TODO: (jef 2017-08-29) Support other types?: lists, dict.
        # Needs: Nothing?
        flds = Country.api_schema['fields']
        typed_params = {
            key: {
                'value': val,
                'type':
                None if val == ''
                else int if val.isdigit()
                else float if '.' in val and val.replace('.', '', 1).isdigit()
                else bool if val.lower() in ('false', 'true')
                else str
            } for key, val in request_args.items()
        }
        if False in [val['type'] == flds[key]['restrictions']['type']
                     for key, val in typed_params.items() if key in flds
                     if flds[key]['restrictions']['queryable']]:
            return False
        return True

    # TODO: (jef 2017-08-29) Insert violation in error message for methods:
    # validate_keys(), validate_queryable(), validate_types().
    # Needs: Validation to be decided on.
    @staticmethod
    def validate_keys(request_args):
        """Validate whether query parameters passed even exist to be queried.

        Args:
            request_args (ImmutableMultiDict): API query parameters.

        Returns:
            tuple: (bool: Validity, str: Error message)
        """
        msg = 'One or more invalid query parameter was passed.'
        flds = Country.api_schema['fields']
        if True in [key not in flds for key in request_args]:
            return False, msg
        return True, ''

    @staticmethod
    def validate_queryable(request_args):
        """Validate whether query parameters are allowed to be queried.

        Args:
            request_args (ImmutableMultiDict): API query parameters.

        Returns:
            tuple: (bool: Validity, str: Error message)
        """
        flds = Country.api_schema['fields']
        if True in [not flds[key]['restrictions']['queryable']
                    for key in request_args if key in flds]:
            return False, 'One or more query params passed is not queryable.'
        return True, ''

    @staticmethod
    def validate_types(request_args):
        """Validate whether query parameter types are correct.

        Args:
            request_args (ImmutableMultiDict): API query parameters.

        Returns:
            tuple: (bool: Validity, str: Error message)
        """
        if not Country.validate_param_types(request_args):
            return False, 'One or more types for query parameters was invalid.'
        return True, ''

    @staticmethod
    def validate_query(request_args):
        """Validate query.

        Args:
            request_args (ImmutableMultiDict): API query parameters.

        Returns:
            bool: True if valid query, else false.
            lit: List of error message strings.
        """
        # TODO: (jef 2017-08.29) Decide on letting the user know if the query
        # was invalid, either in its own response or at the top along with
        # results if we choose to return results when part of the query was
        # invalid. Needs: Validation to be decided on.
        validation_funcs = [Country.validate_keys, Country.validate_queryable,
                            Country.validate_types]
        validities = [func(request_args) for func in validation_funcs]

        return \
            False if False in [status for status, _ in validities] else True, \
            list(filter(None, [messages for _, messages in validities]))

    def url_for(self):
        """Supply URL for resource entity.

        Returns:
            dict: Dict of key 'url' and value of URL for resource entity.
        """
        return {'url': url_for('api.get_country', code=self.code,
                               _external=True)}

    def full_json(self, lang=None, jns=False):
        """Return dictionary ready to convert to JSON as response.

        Args:
            lang (str): The language, if specified.
            jns (bool): If true, namespaces all dictionary keys with prefixed
            table name.

        Returns:
            dict: API response ready to be JSONified.
        """
        result = {
            'id': self.code,
            'order': self.order,
            'subregion': self.subregion,
            'region': self.region,
        }
        # TODO: (jkp 2017-08-29) is it possble that label is null?
        # Needs: Nothing.
        label = self.label.to_string(lang)
        result['label'] = label

        if jns:
            result = self.namespace(result, 'country')

        return result

    def to_json(self, lang=None):
        """Return dictionary ready to convert to JSON as response.

        Contains URL for resource entity.

        Args:
            lang (str): The language, if specified.

        Returns:
            dict: API response ready to be JSONified.
        """
        json_obj = {
            'url': url_for('api.get_country', code=self.code,
                           _external=True),
            'order': self.order,
            'subregion': self.subregion,
            'region': self.region,
            'countryCode': self.code
        }
        if lang is None or lang.lower() == 'en':
            json_obj['label'] = self.label.english
        else:
            lang = lang.lower()
            translations = self.label.translations
            gen = iter(t for t in translations if t.language_code == lang)
            translation = next(gen, None)
            if translation:
                json_obj['label'] = translation.translation
            else:
                json_obj['label'] = url_for(
                    'api.get_text', code=self.label.code, _external=True)
        return json_obj

    def __repr__(self):
        """Return a representation of this object."""
        return '<Country "{}">'.format(self.code)


class Geography(ApiModel):
    """Geography model."""

    __tablename__ = 'geography'
    id = db.Column(db.Integer, primary_key=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    order = db.Column(db.Integer, unique=True)
    subheading_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    type = db.Column(db.String)
    code = db.Column(db.String, unique=True)

    label = db.relationship('EnglishString', foreign_keys=label_id)
    subheading = db.relationship('EnglishString', foreign_keys=subheading_id)
    # TODO (2017-08-29 jkp): Include country backref? Maybe? Delete if a lot of
    # time has passed and no need for this feature

    def __init__(self, **kwargs):
        """Initialize instance of model.

        Does a few things: (1) Updates instance based on mapping from API query
        parameter names to model field names, and (2) calls super init.
        """
        self.update_kwargs_english(kwargs, 'label', 'label_id')
        self.update_kwargs_english(kwargs, 'subheading', 'subheading_id')
        super(Geography, self).__init__(**kwargs)

    @staticmethod
    def none_json(jns=False):
        """Return dictionary ready to convert to JSON as response.

        All values in this dictionary are set to none, serving the cases where
        no data is found or needs to be supplied.

        Args:
            jns (bool): If true, namespaces all dictionary keys with prefixed
            table name.

        Returns:
            dict: API response ready to be JSONified.
        """
        result = {
            'id': None,
            'label': None
        }
        if jns:
            result = ApiModel.namespace(result, 'geography')
        return result

    def __repr__(self):
        """Return a representation of this object."""
        return '<Geography "{}">'.format(self.label.english)

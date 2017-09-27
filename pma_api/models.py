# TODO (jkp 2017-08-29) figure out a way to break this up
# pylint: disable=too-many-lines
"""Model definitions."""
import os
from datetime import datetime
from hashlib import md5

from flask import url_for

from . import db
from .utils import next64


class ApiModel(db.Model):
    """Abstract base model."""

    __abstract__ = True

    ignore_field_prefix = '__'

    def __init__(self, *args, **kwargs):
        """Perform common tasks on kwargs."""
        self.prune_ignored_fields(kwargs)
        self.empty_to_none(kwargs)
        super().__init__(*args, **kwargs)

    @staticmethod
    def prune_ignored_fields(kwargs):
        """Prune ignored fields.

        Args:
            **kwargs: Keyword arguments.
        """
        to_pop = [k for k in kwargs.keys() if
                  k.startswith(ApiModel.ignore_field_prefix)]
        for key in to_pop:
            kwargs.pop(key)

    @staticmethod
    def update_kwargs_date(kwargs, source_key):
        """Update dates to correct format.

        Args:
            kwargs (dict): Keyword arguments.
            source_key (str): The source date string.
        """
        string_date = kwargs[source_key]
        this_date = datetime.strptime(string_date, '%Y-%m-%d')
        kwargs[source_key] = this_date

    @staticmethod
    def update_kwargs_english(kwargs, source_key, target_key):
        """Translate API query parameters to equivalent in model.

        API URL query parameters are in many case abstracted away from the
        models and underlying database. For example, 'survey' in the API would
        equate to 'survey_id' in the database model. Side effects: kwargs are
        modified so that new key of name matching 'target_key' argument is
        inserted, with value as the corresponding record id.

        Args:
            source_key (str): The API query parameter.
            target_key (str): The equivalent model field.
            **kwargs (dict): The keyword argument representation of query
                parameters submitted by the API request.
        """
        english = kwargs.pop(source_key)
        if english:
            record = EnglishString.query.filter_by(english=english).first()
            if record:
                kwargs[target_key] = record.id
            else:
                new_record = EnglishString.insert_unique(english)
                kwargs[target_key] = new_record.id
        else:
            kwargs[target_key] = None

    @staticmethod
    def set_kwargs_id(kwargs, source_key, target_key, model, required=True):
        """Set id of data model field based on code.

        Args:
            source_key (str): Model 'code' field name.
            target_key (str): model 'id' field name.
            model (class): The corresponding SqlAlchemy model class.
            required (bool): True if code required for lookup.
            **kwargs (dict): The keyword argument representation of query
                parameters submitted by the API request.

        Raises:
            KeyError: If identification code for record was not supplied or did
                not resolve.
        """
        code = kwargs.pop(source_key)
        if code == '' and required:
            msg = 'Required key missing "{}" in data source for table "{}"'
            msg = msg.format(source_key, model.__tablename__)
            raise KeyError(msg)
        elif code == '' and not required:
            kwargs[target_key] = None
        else:
            record = model.query.filter_by(code=code).first()
            if record:
                kwargs[target_key] = record.id
            else:
                msg = 'No record with code "{}" in "{}"'
                msg = msg.format(code, model.__tablename__)
                raise KeyError(msg)

    @staticmethod
    def empty_to_none(kwargs):
        """Convert any empty strings to None type.

        Args:
            **kwargs: Keyword arguments.
        """
        for key in kwargs:
            if kwargs[key] == '':
                kwargs[key] = None

    @staticmethod
    def namespace(old_dict, prefix, index=None):
        """Namespaces keys in a dict by doing a prepend to key strings.

        Args:
            old_dict (dict): The original dictionary.
            prefix (str): Prefix to prepend.
            index (int): Optional index to append after the prefix. This is to
                handle situations where a field has one or more sibling fields
                that represent essentially the same variable,
                e.g. "characteristic1", "characteristic2".

        Returns:
            dict: Namespace formatted dictionary.
        """
        if index is not None:
            prefix = prefix + str(index)
        new_dict = {'.'.join((prefix, k)): v for k, v in old_dict.items()}
        return new_dict

    @classmethod
    def get_by_code(cls, lookup):
        """Return an item by code or list of codes.

        Args:
            lookup (str or seq of str): The codes to lookup

        Returns:
            The records that match that code
        """
        if lookup is None:
            return []
        if isinstance(lookup, str):
            query = cls.query.filter(cls.code == lookup)
        else:  # assume it is a sequence of codes
            query = cls.query.filter(cls.code.in_(lookup))
        records = query.all()
        return records


# pylint: disable=too-few-public-methods
class SourceData(db.Model):
    """Metadata."""

    __tablename__ = 'metadata'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String)
    type = db.Column(db.String, index=True)
    md5_checksum = db.Column(db.String)
    blob = db.Column(db.LargeBinary)
    created_on = db.Column(db.DateTime, default=db.func.now(),
                           onupdate=db.func.now(), index=True)

    def __init__(self, path):
        """Metadata init."""
        filename = os.path.splitext(os.path.basename(path))[0]
        self.name = filename
        if filename.startswith('api'):
            self.type = 'api'
        elif filename.startswith('ui'):
            self.type = 'ui'
        self.blob = open(path, 'rb').read()
        self.md5_checksum = md5(self.blob).hexdigest()

    @classmethod
    def get_current_api_data(cls):
        """Return the record for the most recent API data."""
        record = cls.query.filter_by(type='api').first()
        return record

    def to_json(self):
        """Return dictionary ready to convert to JSON as response.

        Returns:
            dict: API response ready to be JSONified.
        """
        result = {
            'name': self.name,
            'hash': self.md5_checksum,
            'type': self.type,
            'createdOn': self.created_on
        }
        return result


class Cache(db.Model):
    """Cache for API responses."""

    __tablename__ = 'cache'
    key = db.Column(db.String, primary_key=True)
    value = db.Column(db.String, nullable=False)
    mimetype = db.Column(db.String)
    source_data_md5 = db.Column(db.String)

    @classmethod
    def get(cls, key):
        """Return a record by key."""
        return cls.query.filter_by(key=key).first()

    def __repr__(self):
        """Give a representation of this record."""
        return "<Cache key='{}'>".format(self.key)


class Indicator(ApiModel):
    """Indicator model."""

    __tablename__ = 'indicator'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'),
                         nullable=False)
    order = db.Column(db.Integer, unique=True)
    type = db.Column(db.String)
    definition_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    level1_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    # Level 2 = Category
    level2_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    # Level 3 = Domain
    level3_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    # TODO: (jkp 2017-08-29) Should this be a translated string?
    # Needs: Nothing?
    denominator = db.Column(db.String)
    measurement_type = db.Column(db.String)
    is_favorite = db.Column(db.Boolean)
    favorite_order = db.Column(db.Integer, unique=True)

    label = db.relationship('EnglishString', foreign_keys=label_id)
    definition = db.relationship('EnglishString', foreign_keys=definition_id)
    level1 = db.relationship('EnglishString', foreign_keys=level1_id)
    # Level 2 = Category
    level2 = db.relationship('EnglishString', foreign_keys=level2_id)
    # Level 3 = Domain
    level3 = db.relationship('EnglishString', foreign_keys=level3_id)

    def __init__(self, **kwargs):
        """Initialize instance of model.

        Does a few things: (1) Updates instance based on mapping from API query
        parameter names to model field names, (2) Reformats any empty strings,
        and (3) Calls super init.
        """
        kwargs['is_favorite'] = bool(kwargs['is_favorite'])
        self.update_kwargs_english(kwargs, 'level1', 'level1_id')
        self.update_kwargs_english(kwargs, 'level2', 'level2_id')
        self.update_kwargs_english(kwargs, 'level3', 'level3_id')
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
        level3_str = self.level3.to_string(lang)

        result['label'] = label_str
        result['definition'] = defn_str
        result['level1'] = level1_str
        result['level2'] = level2_str
        result['level3'] = level3_str

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
        if kwargs:
            kwargs['is_total'] = bool(kwargs['is_total'])
            self.set_kwargs_id(kwargs, 'survey_code', 'survey_id', Survey)
            self.set_kwargs_id(kwargs, 'indicator_code', 'indicator_id',
                               Indicator)
            self.set_kwargs_id(kwargs, 'char1_code', 'char1_id',
                               Characteristic, False)
            self.set_kwargs_id(kwargs, 'char2_code', 'char2_id',
                               Characteristic, False)
            self.empty_to_none(kwargs)
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
        self.update_kwargs_date(kwargs, 'start_date')
        self.update_kwargs_date(kwargs, 'end_date')
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

    def __init__(self, **kwargs):
        """Initialize instance of model.

        Does a few things: (1) Updates instance based on mapping from API query
        parameter names to model field names, and (2) calls super init.
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


class EnglishString(ApiModel):
    """EnglishString model."""

    __tablename__ = 'english_string'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True)
    english = db.Column(db.String, nullable=False)
    translations = db.relationship('Translation')

    def to_string(self, lang=None):
        """Return string in specified language if supplied, else English.

        Args:
            lang (str): The language, if specified.

        Returns:
            str: The text.
        """
        result = self.english
        if lang is not None and lang.lower() != 'en':
            lang = lang.lower()
            gen = iter(t for t in self.translations if t.language_code == lang)
            found = next(gen, None)
            if found is not None:
                result = found.translation
        return result

    def to_json(self):
        """Return dictionary ready to convert to JSON as response.

        Contains URL for resource entity.

        Returns:
            dict: API response ready to be JSONified.
        """
        json_obj = {
            'url': url_for('api.get_text', code=self.code, _external=True),
            'id': self.code,
            'text': self.english,
            'langCode': 'en'
        }
        return json_obj

    @staticmethod
    def insert_unique(english, code=None):
        """Insert a unique record into the database.

        Creates a code and combines with English text to as the parameters for
        new record.

        Args:
            english (str): The string in English to insert.
        """
        # TODO: (jkp 2017-08-29) This is not necessary because next64 now
        # returns unique. Needs: Nothing.
        if code is None:
            code = next64()
        record = EnglishString(code=code, english=english)
        db.session.add(record)
        db.session.commit()
        return record

    def datalab_init_json(self):
        """Datalab init json: EnglishString."""
        this_dict = {
            'en': self.english
        }
        for translation in self.translations:
            this_dict[translation.language_code] = translation.translation
        to_return = {
            self.code: this_dict
        }
        return to_return

    # For the Translation class implementation.
    # def datalab_init_json(self):
    #     """Datalab init json: EnglishString."""
    #     return {'id': self.code,
    #             'string': self.english}

    def __repr__(self):
        """Return a representation of this object."""
        if len(self.english) < 20:
            preview = '{}...'.format(self.english[:17])
        else:
            preview = self.english
        return '<EnglishString {} "{}">'.format(self.code, preview)


class Translation(ApiModel):
    """Translation model."""

    __tablename__ = 'translation'
    id = db.Column(db.Integer, primary_key=True)
    english_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    language_code = db.Column(db.String, nullable=False)
    translation = db.Column(db.String, nullable=False)
    languages_info = {
        'english': {
            'code': 'en',
            'label': 'English',
            'active': True,
            'string_records': 'english'
        },
        'french': {
            'code': 'fr',
            'label': 'French',
            'active': True,
            'string_records': 'To be implemented.'
        }
    }

    def __init__(self, **kwargs):
        """Initialize instance of model.

        Does a few things: (1) Gets english code if it is already supplied and
        creates a record in EnglishString. This happens when inserting a
        record for UI data. Otherwise, gets the english code and (2) Calls
        super init.
        """
        if kwargs.get('english_code'):
            english = EnglishString.insert_unique(
                kwargs['english'], kwargs['english_code'].lower())
            kwargs.pop('english_code')
        else:
            english = EnglishString.query.filter_by(english=kwargs['english'])\
                .first()
        kwargs['english_id'] = english.id
        kwargs.pop('english')
        super(Translation, self).__init__(**kwargs)

    @staticmethod
    def languages():
        """Languages list."""
        languages = {v['code']: v['label'] for _, v in
                     Translation.languages_info.items()}
        return languages

    def __repr__(self):
        """Return a representation of this object."""
        if len(self.translation) < 20:
            preview = '{}...'.format(self.translation[:17])
        else:
            preview = self.translation
        return '<Translation ({}) "{}">'.format(self.language_code, preview)

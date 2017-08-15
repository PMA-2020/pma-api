from datetime import datetime

from flask import url_for
from sqlalchemy.exc import IntegrityError

from . import db
from .utils import next64


class ApiModel(db.Model):
    __abstract__ = True

    ignore_field_prefix = '__'

    @staticmethod
    def prune_ignored_fields(kwargs):
        """Prune ignored fields.

        Args:
            **kwargs: Keyword arguments.
        """
        return {
            key: val for key, val in kwargs.items()
            if not key.startswith(ApiModel.ignore_field_prefix)
        }

    @staticmethod
    def update_kwargs_english(kwargs, source_key, target_key):
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
        for key in kwargs:
            if kwargs[key] == '':
                kwargs[key] = None

    @staticmethod
    def namespace(old_dict, prefix, index=None):
        if index is not None:
            prefix = prefix + str(index)
        new_dict = {'.'.join((prefix, k)): v for k, v in old_dict.items()}
        return new_dict


class Indicator(ApiModel):
    __tablename__ = 'indicator'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    order = db.Column(db.Integer, unique=True)
    type = db.Column(db.String)
    definition_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    level1_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    level2_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    level3_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    # TODO: Should this be a translated string?
    denominator = db.Column(db.String)
    measurement_type = db.Column(db.String)
    is_favorite = db.Column(db.Boolean)
    favorite_order = db.Column(db.Integer, unique=True)

    label = db.relationship('EnglishString', foreign_keys=label_id)
    definition = db.relationship('EnglishString', foreign_keys=definition_id)
    level1 = db.relationship('EnglishString', foreign_keys=level1_id)
    level2 = db.relationship('EnglishString', foreign_keys=level2_id)
    level3 = db.relationship('EnglishString', foreign_keys=level3_id)

    def __init__(self, **kwargs):
        kwargs = self.prune_ignored_fields(kwargs)
        self.update_kwargs_english(kwargs, 'level1', 'level1_id')
        self.update_kwargs_english(kwargs, 'level2', 'level2_id')
        self.update_kwargs_english(kwargs, 'level3', 'level3_id')
        self.update_kwargs_english(kwargs, 'definition', 'definition_id')
        self.update_kwargs_english(kwargs, 'label', 'label_id')
        self.empty_to_none(kwargs)
        super(Indicator, self).__init__(**kwargs)

    def full_json(self, lang=None, jns=False, endpoint=None):
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
        return '<Indicator "{}">'.format(self.code)


class CharacteristicGroup(ApiModel):
    __tablename__ = 'characteristic_group'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    definition_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))

    label = db.relationship('EnglishString', foreign_keys=label_id)
    definition = db.relationship('EnglishString', foreign_keys=definition_id)

    def __init__(self, **kwargs):
        kwargs = self.prune_ignored_fields(kwargs)
        self.update_kwargs_english(kwargs, 'label', 'label_id')
        self.update_kwargs_english(kwargs, 'definition', 'definition_id')
        super(CharacteristicGroup, self).__init__(**kwargs)

    def full_json(self, lang=None, jns=False, index=None):
        result = {
            'id': self.code,
            'label': self.label.to_string(lang),
            'definition': self.definition.to_string(lang)
        }
        if jns:
            result = self.namespace(result, 'charGrp', index=index)
        return result

    def __repr__(self):
        return '<CharacteristicGroup "{}">'.format(self.code)

    @staticmethod
    def none_json(lang=None, jns=False, index=None):
        result = {
            'id': None,
            'label': None,
            'definition': None
        }
        if jns:
            result = ApiModel.namespace(result, 'charGrp', index=index)
        return result


class Characteristic(ApiModel):
    __tablename__ = 'characteristic'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    order = db.Column(db.Integer, unique=True)
    char_grp_id = db.Column(db.Integer, db.ForeignKey('characteristic_group.id'))

    char_grp = db.relationship('CharacteristicGroup')
    label = db.relationship('EnglishString', foreign_keys=label_id)

    def __init__(self, **kwargs):
        kwargs = self.prune_ignored_fields(kwargs)
        self.update_kwargs_english(kwargs, 'label', 'label_id')
        self.set_kwargs_id(kwargs, 'char_grp_code', 'char_grp_id',
                           CharacteristicGroup)
        super(Characteristic, self).__init__(**kwargs)

    def full_json(self, lang=None, jns=False, index=None):
        result = {
            'id': self.code,
            'order': self.order
        }
        result['label'] = self.label.to_string(lang)

        if jns:
            result = self.namespace(result, 'char', index=index)

        char_grp_json = self.char_grp.full_json(lang=lang, jns=True, index=index)

        result.update(char_grp_json)
        return result

    def __repr__(self):
        return '<Characteristic "{}">'.format(self.code)

    @staticmethod
    def none_json(lang=None, jns=False, index=None):
        result = {
            'id': None,
            'order': None,
            'label': None,
        }
        if jns:
            result = ApiModel.namespace(result, 'char', index=index)
        char_grp_json = CharacteristicGroup.none_json(lang, jns=True, index=index)
        result.update(char_grp_json)
        return result


class Data(ApiModel):
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
        kwargs = self.prune_ignored_fields(kwargs)
        self.set_kwargs_id(kwargs, 'survey_code', 'survey_id', Survey)
        self.set_kwargs_id(kwargs, 'indicator_code', 'indicator_id', Indicator)
        self.set_kwargs_id(kwargs, 'char1_code', 'char1_id', Characteristic, False)
        self.set_kwargs_id(kwargs, 'char2_code', 'char2_id', Characteristic, False)
        self.set_kwargs_id(kwargs, 'geo_code', 'geo_id', Geography, False)
        self.empty_to_none(kwargs)
        kwargs['code'] = next64()
        super(Data, self).__init__(**kwargs)

    def full_json(self, lang=None, jns=False):
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
            char1_json = Characteristic.none_json(lang, jns=True, index=1)
        if self.char2 is not None:
            char2_json = self.char2.full_json(lang, jns=True, index=2)
        else:
            char2_json = Characteristic.none_json(lang, jns=True, index=2)
        if self.geo is not None:
            subgeo_json = self.geo.full_json(lang, jns=True)
        else:
            subgeo_json = Geography.none_json(lang, jns=True)

        result.update(survey_json)
        result.update(indicator_json)
        result.update(char1_json)
        result.update(char2_json)
        result.update(subgeo_json)

        return result

    def __repr__(self):
        return '<Data "{}">'.format(self.code)


class Survey(ApiModel):
    __tablename__ = 'survey'
    id = db.Column(db.Integer, primary_key=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    order = db.Column(db.Integer, unique=True)
    type = db.Column(db.String)
    year = db.Column(db.Integer)
    round = db.Column(db.Integer)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    code = db.Column(db.String, unique=True)
    pma_code = db.Column(db.String, unique=True)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'))
    geography_id = db.Column(db.Integer, db.ForeignKey('geography.id'))

    label = db.relationship('EnglishString', foreign_keys=label_id)
    country = db.relationship('Country')
    geography = db.relationship('Geography')

    def url_for(self):
        return {'url': url_for('api.get_survey', code=self.pma_code,
                _external=True)}

    def full_json(self, lang=None, jns=False):
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

    def to_json(self, lang=None):
        return {
            'url': url_for('api.get_survey', code=self.pma_code,
                _external=True),
            'order': self.order,
            'type': self.type,
            'year': self.year,
            'round': self.round,
            'start_date': self.start_date.date().isoformat(),
            'end_date': self.end_date.date().isoformat(),
            'survey_code': self.survey_code,
            'pma_code': self.pma_code,
            'country': self.country.url_for()
        }

    def __init__(self, **kwargs):
        kwargs = self.prune_ignored_fields(kwargs)
        label = kwargs.pop('label', None)
        # country_code = kwargs.pop('country_code', None)
        # geography_code = kwargs.pop('geography_code', None)
        start_date = kwargs.pop('start_date', None)
        end_date = kwargs.pop('end_date', None)
        if not kwargs['label_id']:
            label_eng = EnglishString.query.filter_by(english=label).first()
            if label_eng:
                kwargs['label_id'] = label_eng.id
            else:
                new_label_eng = EnglishString.insert_unique(label)
                kwargs['label_id'] = new_label_eng.id
        self.set_kwargs_id(kwargs, 'country_code', 'country_id', Country,
                           required=True)
        self.set_kwargs_id(kwargs, 'geography_code', 'geography_id', Geography,
                           required=False)
        if start_date:
            kwargs['start_date'] = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            kwargs['end_date'] = datetime.strptime(end_date, '%Y-%m-%d')
        super(Survey, self).__init__(**kwargs)

    def __repr__(self):
        return '<Survey "{}">'.format(self.survey_code)


class Country(ApiModel):
    __tablename__ = 'country'
    id = db.Column(db.Integer, primary_key=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    order = db.Column(db.Integer, unique=True)
    subregion = db.Column(db.String)
    region = db.Column(db.String)
    code = db.Column(db.String, unique=True)

    label = db.relationship('EnglishString', foreign_keys=label_id)

    def __init__(self, **kwargs):
        kwargs = self.prune_ignored_fields(kwargs)
        self.update_kwargs_english(kwargs, 'label', 'label_id')
        super(Country, self).__init__(**kwargs)

    def url_for(self):
        return {'url': url_for('api.get_country', code=self.code,
                _external=True)}

    def full_json(self, lang=None, jns=False):
        result = {
            'id': self.code,
            'order': self.order,
            'subregion': self.subregion,
            'region': self.region,
        }
        # TODO: is it possble that label is null?
        label = self.label.to_string(lang)
        result['label'] = label

        if jns:
            result = self.namespace(result, 'country')

        return result


    def to_json(self, lang=None):
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
            translations = self.label.translations
            translation = next(iter(t for t in translations if t.language_code
                == lang.lower()), None)
            if translation:
                json_obj['label'] = translation.translation
            else:
                json_obj['label'] = url_for('api.get_text',
                    uuid=self.label.uuid, _external=True)
        return json_obj

    def __repr__(self):
        return '<Country "{}">'.format(self.code)


class Geography(ApiModel):
    __tablename__ = 'geography'
    id = db.Column(db.Integer, primary_key=True)
    label_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    order = db.Column(db.Integer, unique=True)
    type = db.Column(db.String)
    code = db.Column(db.String, unique=True)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'))

    label = db.relationship('EnglishString', foreign_keys=label_id)
    country = db.relationship('Country', foreign_keys=country_id)

    @staticmethod
    def none_json(lang=None, jns=False):
        result = {
            'id': None,
            'label': None
        }
        if jns:
            result = ApiModel.namespace(result, 'geography')
        return result

    def __repr__(self):
        return '<Geography "{}">'.format(self.label.english)


class EnglishString(ApiModel):
    __tablename__ = 'english_string'
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String, unique=True)
    english = db.Column(db.String, nullable=False)
    translations = db.relationship('Translation')

    def to_string(self, lang=None):
        result = self.english
        if lang is not None and lang.lower() != 'en':
            found = next(iter(t for t in self.translations if t.language_code
                == lang.lower()), None)
            if found is not None:
                result = found.translation
        return result

    def to_json(self):
        json_obj = {
            'url': url_for('api.get_text', uuid=self.uuid, _external=True),
            'id': self.uuid,
            'text': self.english,
            'langCode': 'en'
        }
        return json_obj

    @staticmethod
    def insert_unique(english):
        # TODO: This is not necessary because next64 now returns unique
        while True:
            try:
                uuid = next64()
                record = EnglishString(uuid=uuid, english=english)
                db.session.add(record)
                db.session.commit()
                return record
            except IntegrityError:
                pass

    def __repr__(self):
        preview = self.english if len(self.english) < 20 else \
                  '{}...'.format(self.english[:17])
        return '<EnglishString {} "{}">'.format(self.uuid, preview)


class Translation(ApiModel):
    __tablename__ = 'translation'
    id = db.Column(db.Integer, primary_key=True)
    english_id = db.Column(db.Integer, db.ForeignKey('english_string.id'))
    language_code = db.Column(db.String, nullable=False)
    translation = db.Column(db.String, nullable=False)

    def __repr__(self):
        preview = self.translation if len(self.translation) < 20 else \
                  '{}...'.format(self.translation[:17])
        return '<Translation ({}) "{}">'.format(self.language_code, preview)

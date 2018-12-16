"""EnglishString & Translation model."""
from . import db
from pma_api.utils import next64


class EnglishString(db.Model):
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
            # 'url': url_for('api.get_text', code=self.code, _external=True),
            'id': self.code,
            'text': self.english,
            'langCode': 'en'
        }
        return json_obj

    @staticmethod
    def insert_or_update(english, code):
        """Insert or update an English record.

        Args:
            english (str): The string in English to insert.
            code (str): The code for the string.

        Returns:
            The EnglishString record inserted or updated.
        """
        record = EnglishString.query.filter_by(code=code).first()
        if record and record.english != english:
            record.english = english
            db.session.commit()
        elif not record:
            record = EnglishString.insert_unique(english, code)
        return record

    @staticmethod
    def insert_unique(english, code=None):
        """Insert a unique record into the database.

        Creates a code and combines with English text to as the parameters for
        new record.

        Args:
            english (str): The string in English to insert.
            code (str): The code for the string. None if it should be random.

        Returns:
            The new EnglishString record.
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

    def __repr__(self):
        """Return a representation of this object."""
        if len(self.english) < 20:
            preview = '{}...'.format(self.english[:17])
        else:
            preview = self.english
        return '<EnglishString {} "{}">'.format(self.code, preview)


class Translation(db.Model):
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
        self.prune_ignored_fields(kwargs)
        if kwargs.get('english_code'):
            english = EnglishString.insert_or_update(
                kwargs['english'], kwargs['english_code'].lower())
            kwargs.pop('english_code')
        else:
            english = EnglishString.query.filter_by(english=kwargs['english'])\
                .first()
        try:
            kwargs['english_id'] = english.id
        except AttributeError:
            new_record = EnglishString.insert_unique(kwargs['english'])
            kwargs['english_id'] = new_record.id

        kwargs.pop('english')
        super(Translation, self).__init__(**kwargs)

    @staticmethod
    def prune_ignored_fields(kwargs):
        """Prune ignored fields.

        Args:
            kwargs (dict): Keyword arguments.
        """
        from pma_api.models.api_base import prune_ignored_fields
        prune_ignored_fields(kwargs)

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

"""Abstract base model."""
from datetime import datetime

from pma_api.config import IGNORE_FIELD_PREFIX
from . import db
from .string import EnglishString


def prune_ignored_fields(kwargs):
    """Prune ignored fields.

    Args:
        kwargs (dict): Keyword arguments.
    """
    to_pop = [k for k in kwargs.keys() if
              k.startswith(ApiModel.ignore_field_prefix)]
    for key in to_pop:
        kwargs.pop(key)


class ApiModel(db.Model):
    """Abstract base model."""

    __abstract__ = True

    ignore_field_prefix = IGNORE_FIELD_PREFIX

    def __init__(self, *args, **kwargs):
        """Perform common tasks on kwargs."""
        self.prune_ignored_fields(kwargs)
        self.empty_to_none(kwargs)
        super().__init__(*args, **kwargs)

    @staticmethod
    def prune_ignored_fields(kwargs):
        """Prune ignored fields.

        Args:
            kwargs (dict): Keyword arguments.
        """
        prune_ignored_fields(kwargs)

    @staticmethod
    def update_kwargs_date(kwargs, source_key, fstr):
        """Update dates to correct format.

        Args:
            kwargs (dict): Keyword arguments.
            source_key (str): The source date string.
            fstr (str): The format string for the date.
        """
        string_date = kwargs[source_key]
        this_date = datetime.strptime(string_date, fstr)
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
            kwargs (dict): The keyword argument representation of query
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

        If the target key is present and it has a value, use that. Otherwise
        use the source key and do a lookup.

        Args:
            source_key (str): Model 'code' field name.
            target_key (str): model 'id' field name.
            model (class): The corresponding SqlAlchemy model class.
            required (bool): True if target key should have an ID.
            kwargs (dict): The keyword argument representation of query
            parameters submitted by the API request.

        Raises:
            KeyError: If identification code for record was not supplied or did
                not resolve.
        """
        code = kwargs.pop(source_key, None)
        fk_id = kwargs.pop(target_key, None)
        empty_code = code == '' or code is None
        empty_fk_id = fk_id == '' or fk_id is None
        if not empty_fk_id:
            kwargs[target_key] = fk_id
        elif empty_code and not required:
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
            kwargs (dict): Keyword arguments.
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

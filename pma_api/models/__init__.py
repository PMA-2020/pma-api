"""Model definitions.

This file defines the doorway for other components into the db_models
sub-package.
"""
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


from .core import (Characteristic, CharacteristicGroup, Country, Data,
                   Geography, Indicator, Survey)
from .meta import Cache, ApiMetadata
from .dataset import Dataset  # Depends on ApiMetadata; so import it after
from .string import EnglishString, Translation
from .user import User

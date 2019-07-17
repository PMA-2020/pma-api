"""Model definitions.

This file defines the doorway for other components into the db_models
sub-package.
"""
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


from pma_api.models.core import Characteristic, CharacteristicGroup, Country, \
    Data, Geography, Indicator, Survey
from pma_api.models.meta import Cache, ApiMetadata
# Depends on ApiMetadata; so import it after
from pma_api.models.dataset import Dataset
from pma_api.models.string import EnglishString, Translation
from pma_api.models.user import User
from pma_api.models.task import Task

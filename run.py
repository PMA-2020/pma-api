"""Run."""
import os

from pma_api import create_app


app = create_app(os.getenv('FLASK_CONFIG', 'default'))

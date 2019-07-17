"""Run."""
import os
from pathlib import Path

# noinspection PyPackageRequirements
from dotenv import load_dotenv

from pma_api import create_app
from pma_api.config import PROJECT_ROOT_PATH


load_dotenv(dotenv_path=Path(PROJECT_ROOT_PATH) / '.env')
app = create_app(os.getenv('ENV_NAME', 'default'))

"""Application manager."""
import csv
import glob
import os

from flask import current_app
from flask_script import Manager, Shell

from pma_api import create_app, db
from pma_api.models import Characteristic
from pma_api.models import CharacteristicGroup
from pma_api.models import Country
from pma_api.models import Data
from pma_api.models import Geography
from pma_api.models import EnglishString
from pma_api.models import Indicator
from pma_api.models import Translation
from pma_api.models import Survey


app = create_app(os.getenv('FLASK_CONFIG', 'default'))
manager = Manager(app)


def make_shell_context():
    """Make shell context.

    Returns:
        dict: Context for application manager shell.
    """
    return dict(app=app, db=db, Country=Country, EnglishString=EnglishString,
                Translation=Translation, Survey=Survey, Indicator=Indicator)
manager.add_command('shell', Shell(make_context=make_shell_context))


def init_from_source(path, Model):
    """Initialize DB table data.

    Initialize table data from csv source data files associated with the
    correspodning data model.

    Args:
        path (str): Path to csv data file.
        Model (class): SqlAlchemy model class.
    """
    with open(path, newline='', encoding='utf-8') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            record = Model(**row)
            db.session.add(record)
        db.session.commit()


@manager.option('--overwrite', help='Drop tables first?', action='store_true')
def initdb(overwrite=False):
    """Create the database.

    Args:
        overwrite (bool): Overwrite database if True, else update.
    """
    with app.app_context():
        if overwrite:
            db.drop_all()
        db.create_all()
        # need to add all data here
        if overwrite:
            src_data_dir = 'data'
            country_csv = os.path.join(src_data_dir, 'country.csv')
            init_from_source(country_csv, Country)
            survey_csv = os.path.join(src_data_dir, 'survey.csv')
            init_from_source(survey_csv, Survey)
            char_grp_csv = os.path.join(src_data_dir, 'char_grp.csv')
            init_from_source(char_grp_csv, CharacteristicGroup)
            char_csv = os.path.join(src_data_dir, 'char.csv')
            init_from_source(char_csv, Characteristic)
            indicator_csv = os.path.join(src_data_dir, 'indicator.csv')
            init_from_source(indicator_csv, Indicator)
            data_csvs = glob.glob(os.path.join(src_data_dir, 'data*.csv'))
            for data in data_csvs:
                init_from_source(data, Data)


if __name__ == '__main__':
    manager.run()

"""Application manager."""
import csv
import glob
import os

from flask import current_app
from flask_script import Manager, Shell
import xlrd

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


def init_from_sheet(ws, model):
    header = None
    for i, row in enumerate(ws.get_rows()):
        row = [r.value for r in row]
        if i == 0:
            header = row
        else:
            row_dict = {k: v for k, v in zip(header, row)}
            record = model(**row_dict)
            db.session.add(record)
    db.session.commit()


model_map = {
    'char': Characteristic,
    'char_grp': CharacteristicGroup,
    'country': Country,
    'data': Data,
    'geography': Geography,
    'indicator': Indicator,
    'survey': Survey,
    'translation': Translation,
}

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
            # 1. Get the source file with all the data
            # 2. Sheet by sheet read in and then row by row
            # 3.
            src_data = 'data/api_data.xlsx'
            with xlrd.open_workbook(src_data) as book:
                for i in range(book.nsheets):
                    ws = book.sheet_by_index(i)
                    if ws.name.startswith('data'):
                        model = Data
                    else:
                        # TODO: make more informative message on KeyError
                        model = model_map[ws.name]
                    init_from_sheet(ws, model)

#            country_csv = os.path.join(src_data_dir, 'country.csv')
#            init_from_source(country_csv, Country)
#            survey_csv = os.path.join(src_data_dir, 'survey.csv')
#            init_from_source(survey_csv, Survey)
#            char_grp_csv = os.path.join(src_data_dir, 'char_grp.csv')
#            init_from_source(char_grp_csv, CharacteristicGroup)
#            char_csv = os.path.join(src_data_dir, 'char.csv')
#            init_from_source(char_csv, Characteristic)
#            indicator_csv = os.path.join(src_data_dir, 'indicator.csv')
#            init_from_source(indicator_csv, Indicator)
#            data_csvs = glob.glob(os.path.join(src_data_dir, 'data*.csv'))
#            for data in data_csvs:
#                init_from_source(data, Data)


if __name__ == '__main__':
    manager.run()

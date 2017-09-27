"""Application manager."""
import csv
import glob
import os

from flask_script import Manager, Shell
import xlrd

from pma_api import create_app, db
from pma_api.models import (Cache, Characteristic, CharacteristicGroup,
        Country, Data, EnglishString, Geography, Indicator, SourceData, Survey,
        Translation)
import pma_api.api_1_0.caching as caching


app = create_app(os.getenv('FLASK_CONFIG', 'default'))
manager = Manager(app)


def get_file_by_glob(pattern):
    """Get file by glob.

    Args:
        pattern (str): A glob pattern.

    Returns:
        str: Path/to/first_file_found
    """
    found = glob.glob(pattern)
    return found[0]


SRC_DATA = get_file_by_glob('./data/api_data*.xlsx')
UI_DATA = get_file_by_glob('./data/ui_data*.xlsx')


ORDERED_MODEL_MAP = (
    ('geography', Geography),
    ('country', Country),
    ('survey', Survey),
    ('char_grp', CharacteristicGroup),
    ('char', Characteristic),
    ('indicator', Indicator),
    ('data', Data)
    # TODO: Add in translations to the excel file
    # ('translation', Translation)
)


UI_ORDERED_MODEL_MAP = (
    ('translation', Translation),
)


def make_shell_context():
    """Make shell context.

    Returns:
        dict: Context for application manager shell.
    """
    return dict(app=app, db=db, Country=Country, EnglishString=EnglishString,
                Translation=Translation, Survey=Survey, Indicator=Indicator,
                Data=Data, Characteristic=Characteristic, Cache=Cache,
                CharacteristicGroup=CharacteristicGroup, SourceData=SourceData)


def init_from_source(path, model):
    """Initialize DB table data from csv file.

    Initialize table data from csv source data files associated with the
    corresponding data model.

    Args:
        path (str): Path to csv data file.
        model (class): SqlAlchemy model class.
    """
    with open(path, newline='', encoding='utf-8') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            record = model(**row)
            db.session.add(record)
        db.session.commit()


def init_from_sheet(ws, model):
    """Initialize DB table data from XLRD Worksheet.

    Initialize table data from source data associated with the corresponding
    data model.

    Args:
        ws (xlrd.sheet.Sheet): XLRD worksheet object.
        model (class): SqlAlchemy model class.
    """
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


def init_from_workbook(wb, queue):
    """Init from workbook.

    Args:
        wb (xlrd.Workbook): Workbook object.
        queue (tuple): Order in which to load models.
    """
    with xlrd.open_workbook(wb) as book:
        for sheetname, model in queue:
            if sheetname == 'data': # actually done last
                for ws in book.sheets():
                    if ws.name.startswith('data'):
                        init_from_sheet(ws, model)
            else:
                ws = book.sheet_by_name(sheetname)
                init_from_sheet(ws, model)

    create_wb_metadata(wb)


def create_wb_metadata(wb_path):
    """Create metadata for Excel Workbook files imported into the DB.

    Args:
        wb_path (str) Path to Excel Workbook.
    """
    record = SourceData(wb_path)
    db.session.add(record)
    db.session.commit()


# TODO: remove --overwrite
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
        if overwrite:
            init_from_workbook(wb=SRC_DATA, queue=ORDERED_MODEL_MAP)
            init_from_workbook(wb=UI_DATA, queue=UI_ORDERED_MODEL_MAP)
            caching.cache_datalab_init(app)


@manager.command
def cache_responses():
    """Cache responses in the 'cache' table of DB."""
    with app.app_context():
        caching.cache_datalab_init(app)


manager.add_command('shell', Shell(make_context=make_shell_context))


if __name__ == '__main__':
    manager.run()

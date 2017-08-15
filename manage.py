"""Application manager."""
import csv
import os

from flask_script import Manager, Shell
import xlrd

from pma_api import create_app, db
from pma_api.models import Characteristic, CharacteristicGroup, Country, Data,\
    Geography, Indicator, Survey, Translation, EnglishString


app = create_app(os.getenv('FLASK_CONFIG', 'default'))
manager = Manager(app)

SRC_DATA_INFO = {
    'path': {
        'dir': './data/',
        'filename': 'api_data',
        'extension': '.xlsx'
    }
}
SRC_DATA = ''.join(str(val) for _, val in SRC_DATA_INFO['path'].items())
AUXILIARY_WORKSHEETS = ('info', 'changelog')

MODEL_MAP = {
    'char': Characteristic,
    'char_grp': CharacteristicGroup,
    'country': Country,
    'data': Data,
    'geography': Geography,
    'indicator': Indicator,
    'survey': Survey,
    'translation': Translation
}
# PRIORITY_MODEL_LOAD_QUEUE = ['geography', 'country']
LOAD_QUEUE = ['translation', 'geography', 'country', 'char_grp', 'char',
              'indicator', 'survey', 'data']


def make_shell_context():
    """Make shell context.

    Returns:
        dict: Context for application manager shell.
    """
    return dict(app=app, db=db, Country=Country, EnglishString=EnglishString,
                Translation=Translation, Survey=Survey, Indicator=Indicator)


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
        queue (list): Order in which to load models.
    """
    # 1. Load DB in order for all non 'data' worksheets.
    with xlrd.open_workbook(wb) as book:
        for present_item in queue:
            for i in range(book.nsheets):
                ws = book.sheet_by_index(i)
                if ws.name in AUXILIARY_WORKSHEETS:
                    continue
                else:
                    if ws.name == present_item:
                        init_from_sheet(ws, MODEL_MAP[ws.name])
    # 2. Handle 'data' worksheets.
        for i in range(book.nsheets):
            ws = book.sheet_by_index(i)
            if ws.name.startswith('data'):
                init_from_sheet(ws, Data)


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
            # TODO: Refactor "shortlist" and "load queue" to be cleaner /
            #   easier to understand.
            # - Note: Some models need to be loaded first due to field values
            #   that are calculated from values in other tables.
            # for priority_model in PRIORITY_MODEL_LOAD_QUEUE:
            init_from_workbook(wb=SRC_DATA, queue=LOAD_QUEUE)
            # init_from_workbook(wb=SRC_DATA)


manager.add_command('shell', Shell(make_context=make_shell_context))


if __name__ == '__main__':
    manager.run()

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
SRC_DATA = ''.join(str(val) for _, val in SRC_DATA_INFO['path'].items())  # path
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
PRIORITY_MODEL_LOAD_QUEUE = ['geography', 'country']

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


@manager.option('--overwrite', help='Drop tables first?', action='store_true')
def initdb(overwrite=False):
    """Create the database.

    Args:
        overwrite (bool): Overwrite database if True, else update.
    """

    def init_from_workbook(wb, shortlist=list()):
        """Init from workbook.

        Args:
            wb (xlrd.Workbook): Workbook object.
            shortlist (list): If supplied, restricted list of worksheets to
                execute on.
        """
        with xlrd.open_workbook(wb) as book:
            for i in range(book.nsheets):
                ws = book.sheet_by_index(i)
                if (shortlist and ws.name not in shortlist) or \
                        (ws.name in AUXILIARY_WORKSHEETS):
                    continue
                else:
                    model = Data if ws.name.startswith('data') \
                        else MODEL_MAP[ws.name]
                    init_from_sheet(ws, model)

    with app.app_context():
        if overwrite:
            db.drop_all()
        db.create_all()
        if overwrite:
            for model in PRIORITY_MODEL_LOAD_QUEUE:
                print(model)
                init_from_workbook(wb=SRC_DATA, shortlist=[model])
            init_from_workbook(wb=SRC_DATA)

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


manager.add_command('shell', Shell(make_context=make_shell_context))


if __name__ == '__main__':
    manager.run()

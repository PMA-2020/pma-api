"""Application manager."""
import csv
import glob
import logging
import os
from sys import stderr

from flask_script import Manager, Shell
import xlrd
from sqlalchemy.exc import DatabaseError, OperationalError

from pma_api import create_app, db
from pma_api.models import (Cache, Characteristic, CharacteristicGroup,
                            Country, Data, EnglishString, Geography, Indicator,
                            ApiMetadata, Survey, Translation, Dataset)
import pma_api.api_1_0.caching as caching


app = create_app(os.getenv('FLASK_CONFIG', 'default'))
manager = Manager(app)
connection_error = '\nError: Was not able to connect to the database. Please '\
    'check that it is running, and your database URL / credentials are ' \
    'correct.\n\n' \
    'Original error message:\n{}'


def get_file_by_glob(pattern):
    """Get file by glob.

    Args:
        pattern (str): A glob pattern.

    Returns:
        str: Path/to/first_file_found
    """
    found = glob.glob(pattern)
    return found[0]


API_DATA = get_file_by_glob('./data/api_data*.xlsx')
UI_DATA = get_file_by_glob('./data/ui_data*.xlsx')


ORDERED_MODEL_MAP = (
    ('geography', Geography),
    ('country', Country),
    ('survey', Survey),
    ('char_grp', CharacteristicGroup),
    ('char', Characteristic),
    ('indicator', Indicator),
    ('translation', Translation),
    ('data', Data)
)


TRANSLATION_MODEL_MAP = (
    ('translation', Translation),
)


def make_shell_context():
    """Make shell context, for the ability to manipulate these models/tables
    from the command line shell.

    Returns:
        dict: Context for application manager shell.
    """
    return dict(app=app, db=db, Country=Country, EnglishString=EnglishString,
                Translation=Translation, Survey=Survey, Indicator=Indicator,
                Data=Data, Characteristic=Characteristic, Cache=Cache,
                CharacteristicGroup=CharacteristicGroup,
                ApiMetadata=ApiMetadata, Dataset=Dataset)


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


def init_data(wb):
    """Put all the data from the workbook into the database."""
    survey = {}
    indicator = {}
    characteristic = {}
    for record in Survey.query.all():
        survey[record.code] = record.id
    for record in Indicator.query.all():
        indicator[record.code] = record.id
    for record in Characteristic.query.all():
        characteristic[record.code] = record.id
    for ws in wb.sheets():
        if ws.name.startswith('data'):
            init_from_sheet(ws, Data, survey=survey, indicator=indicator,
                            characteristic=characteristic)


def init_from_sheet(ws, model, **kwargs):
    """Initialize DB table data from XLRD Worksheet.

    Initialize table data from source data associated with the corresponding
    data model.

    Args:
        ws (xlrd.sheet.Sheet): XLRD worksheet object.
        model (class): SqlAlchemy model class.
    """
    survey, indicator, characteristic = '', '', ''
    if model == Data:
        survey = kwargs['survey']
        indicator = kwargs['indicator']
        characteristic = kwargs['characteristic']
    header = None
    for i, row in enumerate(ws.get_rows()):
        row = [r.value for r in row]
        if i == 0:
            header = row
        else:
            row_dict = {k: v for k, v in zip(header, row)}
            if model == Data:
                survey_code = row_dict.get('survey_code')
                survey_id = survey.get(survey_code)
                row_dict['survey_id'] = survey_id
                indicator_code = row_dict.get('indicator_code')
                indicator_id = indicator.get(indicator_code)
                row_dict['indicator_id'] = indicator_id
                char1_code = row_dict.get('char1_code')
                char1_id = characteristic.get(char1_code)
                row_dict['char1_id'] = char1_id
                char2_code = row_dict.get('char2_code')
                char2_id = characteristic.get(char2_code)
                row_dict['char2_id'] = char2_id
            try:
                record = model(**row_dict)
            except DatabaseError as err:
                msg = 'Error when processing row {} of "{}". ' \
                      'Cell values: {}\n\n' \
                      'Original Error:\n' + str(err)
                msg = msg.format(i+1, ws.name, row)
                logging.error(msg)
                raise
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
            if sheetname == 'data':  # actually done last
                init_data(book)
            else:
                ws = book.sheet_by_name(sheetname)
                init_from_sheet(ws, model)
    create_wb_metadata(wb)


def create_wb_metadata(wb_path):
    """Create metadata for Excel Workbook files imported into the DB.

    Args:
        wb_path (str) Path to Excel Workbook.
    """
    record = ApiMetadata(wb_path)
    db.session.add(record)
    db.session.commit()


@manager.option('--overwrite', help='Drop tables first?', action='store_true')
def initdb(overwrite=False):
    """Create the database.

    Args:
        overwrite (bool): Overwrite database if True, else update.
    """
    with app.app_context():
        try:
            # Delete all tables except for 'datasets'
            if overwrite:
                db.metadata.drop_all(db.engine, tables=[x.__table__ for x in [
                    EnglishString,
                    Data,
                    Translation,
                    Indicator,
                    Characteristic,
                    CharacteristicGroup,
                    Survey,
                    Country,
                    Geography,
                    Cache,
                    ApiMetadata]])

            # Create tables
            db.create_all()

            # Seed database
            if overwrite:
                # TODO: init_from_datasets_table if exists instead?
                init_from_workbook(wb=API_DATA, queue=ORDERED_MODEL_MAP)
                init_from_workbook(wb=UI_DATA, queue=TRANSLATION_MODEL_MAP)
                caching.cache_datalab_init(app)

            # If DB is brand new, seed 'datasets' table too
            database_is_brand_new = list(Dataset.query.all()) == []
            if database_is_brand_new:
                new_dataset = Dataset(file_path=API_DATA)
                db.session.add(new_dataset)
                db.session.commit()

        # Print error if DB background process is not loaded
        except OperationalError as err:
            print(connection_error.format(str(err)), file=stderr)


@manager.command
def translations():
    """Import all translations into the database."""
    with app.app_context():
        try:
            # TODO (jkp 2017-09-28) make this ONE transaction instead of many.
            db.session.query(ApiMetadata).delete()
            db.session.query(Translation).delete()
            db.session.commit()
            init_from_workbook(wb=API_DATA, queue=TRANSLATION_MODEL_MAP)
            init_from_workbook(wb=UI_DATA, queue=TRANSLATION_MODEL_MAP)
            cache_responses()
        except OperationalError as err:
            print(connection_error.format(str(err)), file=stderr)


@manager.command
def cache_responses():
    """Cache responses in the 'cache' table of DB."""
    with app.app_context():
        try:
            caching.cache_datalab_init(app)
        except OperationalError as err:
            print(connection_error.format(str(err)), file=stderr)


manager.add_command('shell', Shell(make_context=make_shell_context))


if __name__ == '__main__':
    manager.run()

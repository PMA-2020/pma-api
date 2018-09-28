#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for dataset class."""
import unittest

from pma_api import db, create_app
from pma_api.models import Dataset


class TestDataset(unittest.TestCase):
    """Test that the dataset class works.

    To run this test directly, issue this command from the root directory:
       python -m test.test_dataset
    """

    def setUp(self):
        """Set up: (1) Put Flask app in test mode, (2) Create temp DB."""
        # Continue from here next time
        # 1 set up the test
        import tempfile
        app = create_app()
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()  # TODO: Will this work?
        app.testing = True
        self.app = app.test_client()
        with app.app_context():
            # 2. new dataset object
            new_dataset = \
                Dataset(file_path ='/Users/richardnguyen5/Documents/Documents/datalab API dev/pma-api/test/file/api_data-2018.03.19-v29-SAS.xlsx')
            # 3. write to db
            db.session.add(new_dataset)
            db.session.commit()

    def test_dataset(self):
        """Create a new entry in 'dataset' table and read data."""
        # 4. read from the db
        dataset_from_db = ''  # write logic to get from db:

        # 5. make assertions
        self.assertTrue(dataset_from_db.ID != '')
        self.assertTrue(dataset_from_db.data != '')
        self.assertTrue(dataset_from_db.datasetDisplayName == 'api_data-2018.03.19-v29-SAS')
        self.assertTrue(type(dataset_from_db.uploadDate) == "<class 'datetime.datetime'>")
        self.assertTrue(dataset_from_db.versionNumber == 'v29')
        self.assertTrue(dataset_from_db.datasetType in ('data', 'metadata', 'full'))
        self.assertTrue(dataset_from_db.isActiveStaging == False)
        self.assertTrue(dataset_from_db.isActiveProduction == False)

    def tearDown(self):
        """Tear down: (1) Close temp DB."""
        # 5: remove the stuff we wrote to the db
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])

# class TestDB(unittest.TestCase):  # TODO: Adapt from tutorial.
#     """Test database functionality.
#
#     Tutorial: http://flask.pocoo.org/docs/0.12/testing/
#     """
#
#     def setUp(self):
#         """Set up: (1) Put Flask app in test mode, (2) Create temp DB."""
#         import tempfile
#         from manage import initdb
#         self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
#         app.testing = True
#         self.app = app.test_client()
#         with app.app_context():
#             initdb()
#
#     def tearDown(self):
#         """Tear down: (1) Close temp DB."""
#         os.close(self.db_fd)
#         os.unlink(app.config['DATABASE'])
#
#     def test_empty_db(self):
#         """Test empty database."""
#         resp = self.app.get('/')
#         assert b'No entries here so far' in resp.data


if __name__ == '__main__':
    unittest.main(TestDataset())

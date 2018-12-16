# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """Unit tests for dataset class."""
# import datetime
# import os
# import unittest
#
# from pma_api import db, create_app
# from pma_api.models import Dataset
#
# from .config import TEST_STATIC_DIR
#
#
# # TODO: incomplete
# class TestDataset(unittest.TestCase):
#     """Test that the dataset class works.
#
#     To run this test directly, issue this command from the root directory:
#        python -m test.test_dataset
#     """
#     file_name = 'api_data-2018.03.19-v29-SAS.xlsx'
#
#     def setUp(self):
#         """Set up: (1) Put Flask app in test mode, (2) Create temp DB."""
#         # Continue from here next time
#         # 1 set up the test
#         import tempfile
#         app = create_app()
#         # TODO: Will this work?
#         self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
#         app.testing = True
#         self.app = app.test_client()
#         with app.app_context():
#             # 2. new dataset object
#             new_dataset = Dataset(
#                 file_path=TEST_STATIC_DIR + TestDataset.file_name)
#             # 3. write to db
#             db.session.add(new_dataset)
#             db.session.commit()
#
#     def test_dataset(self):
#         """Create a new entry in 'dataset' table and read data."""
#         # 4. read from the db
#         dataset_from_db = Dataset.query\
#             .filter_by(dataset_display_name=TestDataset.file_name).first()
#
#         # 5. make assertions
#         self.assertTrue(dataset_from_db.ID != '')
#         self.assertTrue(dataset_from_db.data != '')
#         self.assertTrue(dataset_from_db.dataset_display_name ==
#                         'api_data-2018.03.19-v29-SAS.xlsx')
#         self.assertTrue(type(dataset_from_db.upload_date) ==
#                         datetime.date.today())
#         self.assertTrue(dataset_from_db.version_number == 'v29')
#         self.assertTrue(dataset_from_db.dataset_type in
#                         ('data', 'metadata', 'full'))
#         self.assertTrue(dataset_from_db.is_active_staging is False)
#         self.assertTrue(dataset_from_db.is_active_production is False)
#
#     def tearDown(self):
#         """Tear down: (1) Close temp DB."""
#         # 5: remove the stuff we wrote to the db
#         os.close(self.db_fd)
#         os.unlink(self.app.config['DATABASE'])
#
#
# # TODO: Use this example from tutorial for the above test
# # class TestDB(unittest.TestCase):
# #     """Test database functionality.
# #
# #     Tutorial: http://flask.pocoo.org/docs/0.12/testing/
# #     """
# #
# #     def setUp(self):
# #         """Set up: (1) Put Flask app in test mode, (2) Create temp DB."""
# #         import tempfile
# #         from manage import initdb
# #         self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
# #         app.testing = True
# #         self.app = app.test_client()
# #         with app.app_context():
# #             initdb()
# #
# #     def tearDown(self):
# #         """Tear down: (1) Close temp DB."""
# #         os.close(self.db_fd)
# #         os.unlink(app.config['DATABASE'])
# #
# #     def test_empty_db(self):
# #         """Test empty database."""
# #         resp = self.app.get('/')
# #         assert b'No entries here so far' in resp.data

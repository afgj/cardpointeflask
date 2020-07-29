import os
import time

from flask import current_app
from werkzeug import secure_filename

from celery import states
from celery.exceptions import Ignore
from celery.utils.log import get_task_logger

from cardpointeflask.app import create_celery_app

import pyexcel

from lib.util_dropfiles import CARDPOINTE_KEYS, SALSA_KEYS

LOG = get_task_logger(__name__)

celery = create_celery_app()


@celery.task(bind=True)
def process_files(self, fileList):
    """
    Match cardpointe transactions with salsa forms.

    For now we will simply manipulate csv,xls files but
    eventually we will load data from the database.
    TODO:
      - Write tests
      - Write transactions to database
      - Validate file(s) afterwards
    """
    if fileList and files_are_valid(fileList):
        # Identify cardpointe file and salsa file
        # Get all records from both
        # Set salsa file to be indexed by transaction id
        # Correct form name in cardpointe file
        # Return write final_file to disk

        salsa = {}
        cpointe = []
        for filename in fileList:
            shortname = secure_filename(filename)
            pathname = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                    shortname)
            records = pyexcel.get_records(file_name=pathname)
            keys = records[1].keys()

            if keys == SALSA_KEYS:
                for row in records:
                    transaction_id = str(row['transaction pnref'])
                    salsa[transaction_id] = row

            elif keys == CARDPOINTE_KEYS:
                cpointe = records

        if salsa and cpointe:
            for index, row in enumerate(cpointe):
                transaction = row['Transaction #'][1:]
                form_name = salsa[transaction]['activity form name']
                cpointe[index]['FORM_NAME (Custom Field #0)'] = form_name
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': format(index/len(cpointe), '.2f'),
                        'total': 100, 'status': 'PROCESSING'})

            f = 'cardpointe' + time.strftime("%Y%m%d-%H%M%S") + '.csv'
            p = os.path.join(current_app.config['UPLOAD_FOLDER'], f)

            pyexcel.save_as(
                records=cpointe,
                dest_file_name=p,
                dest_delimiter=',')
            return {
                'current': 100,
                'total': 100,
                'status': 'Task completed!',
                'result': f}
    self.update_state(state=states.FAILURE)
    raise Ignore()


def files_are_valid(fileList):
    """ Make sure files are valid to be processed """
    if len(fileList) != 2:
        return False
    valid_keys = CARDPOINTE_KEYS | SALSA_KEYS
    for f in fileList:
        file_d = pyexcel.get_dict(file_name=os.path.join(current_app.config['UPLOAD_FOLDER'], f),\
            name_columns_by_row=0)
        for key in file_d.keys():
            if key not in valid_keys:
                return False
    return True

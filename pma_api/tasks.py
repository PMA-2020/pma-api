"""Tasks"""
import celery


@celery.task(bind=True)
def apply_dataset(self):
    """TODO"""
    # receive a dataset param
    # receive target server

    # post request to server to: upload dataset
    self.update_state(state='PROGRESS',
                      meta={'status': 'TODO'})

    # post request to server to: run db script
    # db script starts and state updates accordingly
    self.update_state(state='PROGRESS',
                      meta={'status': 'TODO'})

    # db script finishes and state updates accordingly
    self.update_state(state='PROGRESS',
                      meta={'status': 'TODO'})


    return {'status': ''}
x
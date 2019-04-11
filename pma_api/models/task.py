"""Metadata table."""
from typing import List

from pma_api.app import PmaApiFlask
from pma_api.utils import get_app_instance

from pma_api.models import db


app: PmaApiFlask = get_app_instance()


class Task(db.Model):
    """Tasks

    Attribute 'id' is not auto-generated / auto-incremented, but is actually
    a unique task ID assigned by celery.
    """
    __tablename__ = 'task'

    id = db.Column(db.String, primary_key=True)
    is_active = db.Column('is_active', db.Boolean(), nullable=False)

    def __init__(self, task_id: str, is_active: bool = False):
        """Task init"""
        self.id = task_id
        self.is_active = is_active

    @classmethod
    def register_active(cls, task_id: str):
        """Register task as active

        Side effects:
            - Adds record to DB if doesn't exist
            - Modifies record
        """
        with app.app_context():
            task: Task = cls.query.filter_by(id=task_id).first()
            if not task:
                task = cls(task_id=task_id, is_active=True)
                db.session.add(task)
            else:
                task.is_active = True
            db.session.commit()

    @classmethod
    def register_inactive(cls, task_id: str):
        """Register task as inactive

        Side effects:
            - Modifies record
        """
        with app.app_context():
            task: Task = cls.query.filter_by(id=task_id).first()
            task.is_active = False
            db.session.commit()

    @classmethod
    def get_present_tasks(cls, validate: bool = True, update: bool = True) \
            -> List[str]:
        """Get list of IDs for active tasks

        Side effects:
            - Modifies records if update arg is True

        Args:
            validate (bool): If True, will query task queue message broker to
             see if tasks marked as active in the PMA API db are in fact
             correctly marked as such. If update arg is True, validation will
             also run validation even if the arg validate is False.
            update (bool): If True, will: (1) also set validation to True, (2)
             also modify records to correctly mark them as inactive if they
             fail to validate as active tasks.

        TODO 2019.04.15-jef: Ideally, we want to use a more standard way to get
         a list of present (active/scheduled/reserved tasks). Unfortunately,
         there are some issues making this difficult in Celery 4. Presently,
         best solution seems to be either: a. downgrade to Celery 3, or b. use
         rabbitmq-admin available on pip. Useful link: https://stackoverflow.
         com/questions/5544629/retrieve-list-of-tasks-in-a-queue-in-celery

        Returns:
            list(str): Present tasks
        """
        from pma_api.task_utils import validate_active_task_status

        validation: bool = True if update or validate else False
        with app.app_context():
            all_tasks: List[Task] = cls.query.all()
            tasks: List[Task] = [x for x in all_tasks if x.is_active]
        actually_inactive_tasks: List[Task] = [] if not validation else \
            [x for x in tasks if not validate_active_task_status(x.id)]

        if update:
            for x in actually_inactive_tasks:
                x.is_active = False
            with app.app_context():
                db.session.commit()

        task_ids: List[str] = [x.id for x in tasks] if not validation else \
            [x.id for x in tasks if x not in actually_inactive_tasks]

        return task_ids

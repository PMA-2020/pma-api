"""Multistep Task super class"""
from collections import OrderedDict
from copy import copy
from typing import List, Dict, Union, Generator

from pma_api.error import PmaApiException
from pma_api.manage.functional_subtask import FunctionalSubtask


class MultistepTask:
    """A synchronous multi-step task

    Subtasks groups are of the form:
    Dict[str, Dict[str, Union[str, int, Callable]]] = {
            'subtask_1_name': {
                'prints': 'Doing first thing',
                'pct_starts_at': 0
            },
            'subtask_2_name': {
                'prints': 'Doing second thing',
                'pct_starts_at': 10
            ...
    }

    Or it could be of the form:
            'subtask_1_name': <subtask obj>

    This class is meant to be used either by itself, in which print statements
    are typically made to show task progress, or in tandem with a task queue
    such as Celery, where a callback is utilized to report progress.

    With each call to `begin(<subtask>)`, progress is reported, utilizing each
    sub-task objects' print statement and percentage. When creating a sub-task
    to build up a sub-task dictionary as shown above, it is necessary to assign
    semi-arbitrary percentages. These percentages will represent the task
    authors' best guess at how long a task should take.
    """

    start_status = 'PENDING'

    def __init__(
            self, silent: bool = False, name: str = '',
            callback: Generator = None,
            subtasks: Dict = None):
        """Tracks progress of task queue

        If queue is empty, calls to TaskTracker methods will do nothing.

        Args:
            subtasks: Queue'd dictionary of subtasks to run.
            silent: Don't print updates?
            callback: Callback function to use for every iteration
            of the queue. This callback must take a single dictionary as its
            parameter, with the following schema...
                {'status': str, 'current': float}
            ...where the value of 'current' is a float with value between 0
            and 1.
        """
        self.subtasks = subtasks if subtasks else OrderedDict()
        self.silent = silent
        self.name = name
        self.callback = callback
        self.tot_sub_tasks = len(subtasks.keys()) if subtasks else 0
        self.status = self.start_status
        self.completion_ratio = float(0)

    @staticmethod
    def _calc_subtask_grp_pcts(
            subtask_grp_list: List[Dict[str, Union[Dict, FunctionalSubtask]]],
            start: float, stop: float) \
            -> Dict:
        """Calculate percents that each subtask in group should start at.

        Args:
            subtask_grp_list: Collection of subtasks in form of a list.
            start: Percent that the first subtask should start at.
            stop: Percent that the *next* subtask should start at. The last
            subtask in group will not start at this number, but before it.

        Return
            Collection of subtasks in form of a dictionary.
        """
        subtask_grp_dict = {}

        pct_each_consumes = (stop - start) / len(subtask_grp_list)
        pct_each_begins = [start]
        for i in range(len(subtask_grp_list) - 1):
            pct_each_begins.append(pct_each_begins[-1] + pct_each_consumes)

        is_functional_subtask: bool = isinstance(
            list(subtask_grp_list[0].values())[0], FunctionalSubtask)

        if not is_functional_subtask:
            subtask_grp_list_calculated = []
            for subtask in subtask_grp_list:
                calculated_subtask = copy(subtask)
                subtask_name: str = list(subtask.keys())[0]
                pct_start: float = pct_each_begins.pop(0)
                calculated_subtask[subtask_name]['pct_starts_at'] = pct_start
                subtask_grp_list_calculated.append(calculated_subtask)

            for subtask in subtask_grp_list_calculated:
                for k, v in subtask.items():
                    subtask_grp_dict[k] = v
        else:
            for item in subtask_grp_list:
                for subtask_name, subtask in item.items():
                    pct_start: float = pct_each_begins.pop(0)
                    subtask.pct_starts_at = pct_start
                    subtask_grp_dict[subtask_name] = subtask

        return subtask_grp_dict

    def _report(self, silence_status: bool = False,
                silence_percent: bool = False):
        """Report progress

        Args:
            silence_status (bool): Silence status?
            silence_percent (bool): Silence percent?
        """
        if not self.status or self.completion_ratio:
            return
        if not self.silent:
            pct: str = str(int(self.completion_ratio * 100)) + '%'
            msg = ' '.join([
                self.status if not silence_status else '',
                '({})'.format(pct) if not silence_percent else ''
            ])
            print(msg)
        if self.callback:
            self.callback.send({
                'name': self.name,
                'status': self.status,
                'current': self.completion_ratio})

    def _begin_subtask(self, subtask_name: str,
                       subtask_queue: OrderedDict = None):
        """Begin subtask. Prints/returns subtask message and percent

        Side effects:
            - self._report
            - Runs subtask function if present

        Args:
            subtask_name: Name of subtask to report running. If absent,
            prints that task has already begun.
            subtask_queue: Ordered dictionary of subtasks to run
        """
        subtask_queue: OrderedDict = subtask_queue if subtask_queue \
            else self.subtasks
        if not subtask_queue:
            return
        subtask: Union[Dict, FunctionalSubtask] = subtask_queue[subtask_name]

        pct: float = subtask['pct_starts_at'] if isinstance(subtask, dict) \
            else subtask.pct_starts_at
        self.completion_ratio = float(pct if pct < 1 else pct / 100)
        self.status: str = subtask['prints'] if isinstance(subtask, dict) \
            else subtask.prints

        self._report()
        if isinstance(subtask, dict):
            if subtask['func']:
                subtask['func']()
        else:
            if hasattr(subtask, 'func'):
                subtask.func()

    def _begin_task(self):
        """Begin multistep task. Prints/returns task name.

        Side effects:
            - Sets instance attributes
            - self._report

        Raises:
            PmaApiException: If task was called to begin more than once.
        """
        err = 'Task \'{}\' has already started, but a call was made to ' \
              'start it again. If intent is to start a subtask, subtask name' \
              ' should be passed when calling'.format(self.name)
        if self.status != self.start_status:
            raise PmaApiException(err)

        if not self.subtasks:
            return

        self.completion_ratio: float = float(0)
        self.status: str = 'Task start: ' + \
                           ' {}'.format(self.name) if self.name else ''
        self._report(silence_percent=True)

    def begin(self, subtask_name: str = '',
              subtask_queue: OrderedDict = None):
        """Register and report task or subtask begin

        Side effects:
            - self._begin_multistep_task
            - self._begin_subtask

        Args:
            subtask_name: Name of subtask to report running. If absent,
            prints that task has already begun.
            subtask_queue: Ordered dictionary of subtasks to run
        """
        if not subtask_name:
            self._begin_task()
        else:
            self._begin_subtask(
                subtask_name=subtask_name,
                subtask_queue=subtask_queue)

    def complete(self, seconds_elapsed: int = None):
        """Register and report all sub-tasks and task itself complete"""
        if not self.subtasks:
            return

        self.completion_ratio: float = float(1)
        if self.name and seconds_elapsed:
            self.status = 'Task completed in {} seconds:  {}'\
                .format(str(seconds_elapsed), self.name)
        elif self.name:
            self.status = 'Task complete:  {}'.format(self.name)
        else:
            self.status = ''

        self._report()

"""Functional Subtask"""
from typing import Callable, Dict


class FunctionalSubtask:
    """A single granule of a multistep task; runs a simple function.

    Can be sync or async.
    """

    def __init__(self, name: str, prints: str, pct_starts_at: float,
                 func: Callable = None, *args, **kwargs):
        """Initializer

        name (str): Subtask name
        prints (str): A string that the subtask will return to be printed out
        pct_starts_at (float): The percent that subtask is expected to begin
        within a larger group of subtasks.
        func (Callable): A function to run
        """
        self.name: str = name
        self.prints: str = prints
        self.pct_starts_at: float = pct_starts_at
        self.func_ref: Callable = func
        self.args: tuple = args
        self.kwargs: Dict = kwargs

    def func(self):
        """Runs function w/ arguments 'args' or keyword arguments 'kwargs'."""
        self.func_ref(*self.args, **self.kwargs)

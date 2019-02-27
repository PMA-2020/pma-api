"""Suppress stdout and stderr

TODO: Allow stderr and stdout to be stored and retrieved later.
"""
import os
import sys
from io import StringIO
from contextlib import contextmanager


class SuppressStdoutStderr(object):
    """Suppress stdout and stderr

    A context manager for doing a "deep suppression" of stdout and stderr in
    Python, i.e. will suppress all print, even if the print originates in a
    compiled C/Fortran sub-function.

    This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).

    Usage:
        with SuppressStdoutStderr():
            # your code here
    """

    def __init__(self):
        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = [os.dup(1), os.dup(2)]

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        # Close all file descriptors
        for fd in self.null_fds + self.save_fds:
            os.close(fd)

    @staticmethod
    @contextmanager
    def capture_stderr_only(func, *args, **kwargs) -> str:
        """Capture stderr

        Args:
            func: A function

        Returns:
            str: Output of sys.stderr
        """
        out, sys.stderr = sys.stderr, StringIO()
        try:
            func(*args, **kwargs)
            sys.stderr.seek(0)
            yield sys.stderr.read()
        finally:
            sys.stderr = out

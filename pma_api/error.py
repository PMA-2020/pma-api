"""Errors and exceptions"""


class PmaApiException(Exception):
    """Base exception for package"""

    def __init__(self, *args: str, **kwargs):
        # kwargs appear in Exception def; not sure why Pycharm doesn't see
        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)


class PmaApiDbInteractionError(PmaApiException):
    """Broad class for exceptions related to DB interactions"""


class ExistingDatasetError(PmaApiDbInteractionError):
    """Dataset already exists in db"""


class PmaApiTaskDenialError(PmaApiException):
    """Task denial exception"""
    msg = 'There is currently a task actively running. A request to start a ' \
          'new, concurrent task was made, but has been denied.'

    def __init__(self, *args: str, **kwargs):
        if args:
            super().__init__(*args, **kwargs)
        else:
            super().__init__(PmaApiTaskDenialError.msg, **kwargs)

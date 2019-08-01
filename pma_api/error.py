"""Errors and exceptions"""


class PmaApiException(Exception):
    """Base exception for package"""

    # def __init__(self, *args: str, **kwargs):
    #     # kwargs appear in Exception def; not sure why Pycharm doesn't see
    #     # noinspection PyArgumentList
    #     super().__init__(*args, **kwargs)
    def __init__(self, *args: str, **kwargs):
        # noinspection PyUnresolvedReferences
        msg: str = \
            self.__class__.__name__ + ': ' + self.__class__.msg \
            if hasattr(self.__class__, 'msg') else ''
        if args:
            super().__init__(*args, **kwargs)
        elif msg:
            super().__init__(msg, **kwargs)
        else:
            super().__init__(*args, **kwargs)


class PmaApiDbInteractionError(PmaApiException):
    """Broad class for exceptions related to DB interactions"""


class ExistingDatasetError(PmaApiDbInteractionError):
    """Dataset already exists in db"""


class MalformedApiDatasetError(PmaApiException):
    """Malformed Api Dataset Error"""
    msg = 'The supplied file is either not a PMA API spec dataset file' \
          ', or is in some way malformed. Please make sure that the file is ' \
          'conforms to the requirements for a PMA API spec dataset file as ' \
          'described in the docs: http://api-docs.pma2020.org/content/' \
          'data_managers/data_managers.html#pma-api-dataset-files'


class PmaApiTaskDenialError(PmaApiException):
    """Task denial exception"""
    msg = 'There is currently a task actively running. A request to start a ' \
          'new, concurrent task was made, but has been denied.'

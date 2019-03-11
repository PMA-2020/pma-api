"""Errors and exceptions"""


class PmaApiException(Exception):
    """Base exception for package"""


class InvalidDataFileError(PmaApiException):
    """Data file was not valid"""


class PmaApiServerError(PmaApiException):
    """Broad class for exceptiosn related to server"""


class PmaApiDbInteractionError(PmaApiException):
    """Broad class for exceptions related to DB interactions"""


class ExistingDatasetError(PmaApiDbInteractionError):
    """Dataset already exists in db"""


class DatasetNotFoundError(PmaApiDbInteractionError):
    """Dataset was not found in db"""

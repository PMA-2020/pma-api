"""Errors and exceptions"""


class PmaApiException(Exception):
    """Base exception for package"""


class PmaApiDbInteractionError(PmaApiException):
    """Braod class for exceptions related to DB interactions"""


class ExistingDatasetError(PmaApiException):
    """Dataset already exists in db"""


class InvalidDataFileError(PmaApiException):
    """Data file was not valid"""


class PmaApiServerError(PmaApiException):
    """Broad class for exceptiosn related to server"""

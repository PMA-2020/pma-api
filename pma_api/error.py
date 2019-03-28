"""Errors and exceptions"""


class PmaApiException(Exception):
    """Base exception for package"""


class PmaApiDbInteractionError(PmaApiException):
    """Broad class for exceptions related to DB interactions"""


class ExistingDatasetError(PmaApiDbInteractionError):
    """Dataset already exists in db"""

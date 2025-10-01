"""Custom exceptions."""


class RecorulesError(Exception):
    """Base exception for recorules."""


class InvalidRecoruLoginError(RecorulesError):
    """Raised when Recoru login fails."""


class NoClockInError(RecorulesError):
    """Raised when no clock-in time is found."""


class ConfigNotFoundError(RecorulesError):
    """Raised when configuration is not found."""

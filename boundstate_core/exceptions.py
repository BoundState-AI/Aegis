"""
BoundState Core Exceptions.

Minimal exception classes for safety-critical operations.
"""


class BoundStateError(Exception):
    """Base exception for all BoundState errors."""

    pass


class SafetyCriticalError(BoundStateError):
    """
    Exception raised for safety-critical failures.

    Use this exception when a failure could have safety implications,
    such as incorrect PFAS risk assessments or regulatory compliance issues.
    """

    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message)
        self.context = context or {}

    def __str__(self) -> str:
        if self.context:
            return f"{super().__str__()} | Context: {self.context}"
        return super().__str__()


class ValidationError(BoundStateError):
    """Exception raised for data validation failures."""

    pass


class ConfigurationError(BoundStateError):
    """Exception raised for configuration issues."""

    pass

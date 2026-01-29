"""
BoundState Core - Shared infrastructure for BoundState AI products.
"""

from boundstate_core.exceptions import (
    BoundStateError,
    SafetyCriticalError,
    ValidationError,
    ConfigurationError,
)

__version__ = "1.0.0"

__all__ = [
    "BoundStateError",
    "SafetyCriticalError",
    "ValidationError",
    "ConfigurationError",
]

#!/usr/bin/env python3
"""
Module: exceptions
Purpose: AEGIS exceptions module for safety-critical error handling.
    Provides SafetyCriticalError integration with boundstate_core and
    defines exception hierarchy for pathway traversal and graph building.

    Rev History:
        1.0.0 - Initial exceptions with SafetyCriticalError fallback

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# Try to import from boundstate_core, fall back to local definition
try:
    from boundstate_core.exceptions import SafetyCriticalError
except ImportError:
    logger.debug("boundstate_core not available, using local SafetyCriticalError definition")

    class SafetyCriticalError(Exception):
        """
        Exception for safety-critical errors in PFAS risk assessment.

        This exception should be raised when:
        - Data integrity issues are detected
        - Critical pathway calculations fail
        - Regulatory data is inconsistent or missing
        """

        def __init__(self, message: str, context: dict | None = None):
            super().__init__(message)
            self.context = context or {}


class AEGISValidationError(Exception):
    """Raised when input validation fails."""

    pass


class PathwayTraversalError(Exception):
    """Raised when pathway traversal encounters an error."""

    pass


class GraphBuildError(SafetyCriticalError):
    """Raised when knowledge graph construction fails."""

    pass


__all__ = [
    "SafetyCriticalError",
    "AEGISValidationError",
    "PathwayTraversalError",
    "GraphBuildError",
]

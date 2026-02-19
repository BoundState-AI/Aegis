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

from boundstate_core.exceptions import SafetyCriticalError


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

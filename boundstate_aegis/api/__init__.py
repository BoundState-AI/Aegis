#!/usr/bin/env python3
"""
Module: api
Purpose: AEGIS API layer providing FastAPI endpoints for PFAS risk assessment.
    Exports create_app factory function for application initialization.

    Rev History:
        1.0.0 - Initial API package

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from boundstate_aegis.api.aegis_api import create_app

__all__ = ["create_app"]

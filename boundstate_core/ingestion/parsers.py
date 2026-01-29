# boundstate_core/ingestion/parsers.py
"""
Document parsers - Backwards Compatibility Wrapper.

This module re-exports the parsers from the new package structure.
The actual implementations are now in:
- boundstate_core/ingestion/parsers/base.py
- boundstate_core/ingestion/parsers/pdf_parser.py
- boundstate_core/ingestion/parsers_legacy.py

For new code, prefer importing from the package:
    from boundstate_core.ingestion.parsers import get_parser

Compliance: SWE-033 (Requirements Traceability)
"""
from __future__ import annotations

__safety_critical__ = False  # NASA SWE-013

# Re-export everything from the package
from boundstate_core.ingestion.parsers import (
    # Base
    DocumentParser,
    _clean_text,
    _is_mostly_line_junk,
    find_poppler_path,
    # Parsers
    PdfParser,
    DocxParser,
    ExcelParser,
    TextParser,
    MarkdownParser,
    PowerPointParser,
    CadParser,
    ImageParser,
    JSONParser,
    VideoRawParser,
    # Factory
    get_parser,
)

__all__ = [
    "DocumentParser",
    "_clean_text",
    "_is_mostly_line_junk",
    "find_poppler_path",
    "PdfParser",
    "DocxParser",
    "ExcelParser",
    "TextParser",
    "MarkdownParser",
    "PowerPointParser",
    "CadParser",
    "ImageParser",
    "JSONParser",
    "VideoRawParser",
    "get_parser",
]

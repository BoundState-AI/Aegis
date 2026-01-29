# boundstate_core/ingestion/parsers/__init__.py
"""
Document parsers for various file formats.

This package provides parsers for PDF, DOCX, Excel, PowerPoint, and other
document formats. Each parser extracts structured sections with metadata.

Structure:
- base.py: DocumentParser base class and utilities
- pdf_parser.py: PdfParser (migrated from legacy)
- parsers_legacy.py: Remaining parsers (to be migrated incrementally)

Usage:
    from boundstate_core.ingestion.parsers import get_parser, PdfParser

Compliance: SWE-033 (Requirements Traceability)
"""
from __future__ import annotations

__safety_critical__ = False  # NASA SWE-013

# Import base class and utilities
from boundstate_core.ingestion.parsers.base import (
    DocumentParser,
    _clean_text,
    _is_mostly_line_junk,
    find_poppler_path,
)

# Import migrated parsers
from boundstate_core.ingestion.parsers.pdf_parser import PdfParser

# Import legacy parsers (will be migrated incrementally)
from boundstate_core.ingestion.parsers_legacy import (
    DocxParser,
    ExcelParser,
    TextParser,
    MarkdownParser,
    PowerPointParser,
    CadParser,
    ImageParser,
    JSONParser,
    VideoRawParser,
    get_parser,
)

__all__ = [
    # Base
    "DocumentParser",
    "_clean_text",
    "_is_mostly_line_junk",
    "find_poppler_path",
    # Parsers (migrated)
    "PdfParser",
    # Parsers (legacy)
    "DocxParser",
    "ExcelParser",
    "TextParser",
    "MarkdownParser",
    "PowerPointParser",
    "CadParser",
    "ImageParser",
    "JSONParser",
    "VideoRawParser",
    # Factory
    "get_parser",
]

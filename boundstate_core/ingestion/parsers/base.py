# boundstate_core/ingestion/parsers/base.py
"""
Base document parser class and utilities.

Provides the DocumentParser abstract base class that all format-specific
parsers inherit from, plus shared utility functions.

Compliance: SWE-033 (Requirements Traceability)
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
"""
from __future__ import annotations

__safety_critical__ = False  # NASA SWE-013: Document parsing is not safety-critical

import os
import re
import unicodedata
import logging
from typing import List, Dict, Any, Optional

from boundstate_core.config.utils import (
    parse_version,
    extract_version_and_id,
    clean_text,
    secure_filename,
)

logger = logging.getLogger(__name__)


def _clean_text(text: str) -> str:
    """Clean visual junk like table borders and normalize spacing."""
    text = re.sub(r"[│┃╱╲╳═║╔╗╝╚╩╦╬━┻┳┏┓┛┗─—–•·…]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _is_mostly_line_junk(text: str, threshold: float = 0.6) -> bool:
    """Check if text is mostly visual symbols (lines, boxes, etc)."""
    junk_chars = re.findall(r"[│┃╱╲╳═║╔╗╝╚╩╦╬━┻┳┏┓┛┗─—–•·…]", text)
    return len(junk_chars) / max(1, len(text)) > threshold


def find_poppler_path() -> Optional[str]:
    """Find poppler binaries path for pdf2image."""
    import shutil
    import platform

    # Check if pdftoppm is in PATH
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        return os.path.dirname(pdftoppm)

    if platform.system() == "Windows":
        # Check conda environment first
        conda_env = os.environ.get("CONDA_PREFIX")
        if conda_env:
            conda_poppler = os.path.join(conda_env, "Library", "bin")
            if os.path.exists(os.path.join(conda_poppler, "pdftoppm.exe")):
                return conda_poppler

        # Common Windows paths
        common_paths = [
            r"C:\Program Files\poppler\Library\bin",
            r"C:\Program Files (x86)\poppler\Library\bin",
            r"C:\poppler\Library\bin",
        ]

        for path in common_paths:
            if os.path.exists(os.path.join(path, "pdftoppm.exe")):
                return path

    return None


class DocumentParser:
    """Base class for document parsers."""

    def __init__(
        self,
        file_path: str,
        file_bytes: Optional[bytes] = None,
        doc_type: Optional[str] = None,
    ):
        self.file_path = secure_filename(os.path.basename(file_path))
        self.full_path = file_path
        self.file_bytes = file_bytes
        self.doc_type_override = doc_type
        self.base_doc_id, self.version_str = extract_version_and_id(self.file_path)
        self.version_tuple = parse_version(self.version_str)
        self.sections: List[Dict[str, Any]] = []

    def parse(self) -> List[Dict[str, Any]]:
        """Parse the document. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement parse()")

    def _is_form_content(self, text: str) -> bool:
        """Detect if text resembles a form or questionnaire."""
        form_pattern = re.compile(r"^\d+\.\d+\s+[^?]+?\?", re.MULTILINE)
        numbered_pattern = re.compile(r"^\d+\.\d+\s+", re.MULTILINE)
        return bool(form_pattern.search(text)) or len(numbered_pattern.findall(text)) > 3

    def _extract_title_from_chunk(self, chunk_text: str, chunk_num: int) -> str:
        """Extract a meaningful title from chunk text."""
        lines = chunk_text.split("\n")
        for line in lines[:3]:
            line = line.strip()
            if line and len(line) < 100:
                if re.match(r"^\d+\.[\d\s]*\w", line) or any(
                    keyword in line.lower()
                    for keyword in [
                        "purpose",
                        "process",
                        "introduction",
                        "section",
                        "appendix",
                        "reference",
                    ]
                ):
                    return line

        words = chunk_text.split()[:10]
        if len(words) > 3:
            return " ".join(words[:5]) + "..."

        return f"Section {chunk_num}"

    def _extract_header_metadata(self, text: str) -> Dict[str, Any]:
        """Extract header metadata (e.g., company info, certifications)."""
        header_lines = []
        for line in text.split("\n")[:15]:
            if line.strip() and not line.startswith(
                ("F1740", "G1301", "G1800", "Page ", "Amentum", "Rev.", "Effective")
            ):
                header_lines.append(line.strip())
        return {"header_info": " | ".join(header_lines)} if header_lines else {}

    def _clean_ocr_text(self, text: str) -> str:
        """Clean OCR-extracted text for better parsing."""
        text = unicodedata.normalize("NFKD", text)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        text = re.sub(r"\s{2,}", " ", text)
        text = re.sub(r"(\n\s*){2,}", "\n\n", text)
        footer_patterns = [
            r"Page \d+ of \d+",
            r"Amentum Proprietary",
            r"F\d{4}\.\d+[A-Z]? Rev\. \d+ Effective \d{4}-\d{2}-\d{2}",
            r"G\d{4}\.\d+[A-Z]? Rev\. \d+ Effective \d{4}-\d{2}-\d{2}",
            r"Copyright.*Amentum.*rights reserved",
        ]
        for pattern in footer_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        return text.strip()

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences for finer granularity."""
        sentence_pattern = r"(?<=[.!?;])\s+"
        sentences = re.split(sentence_pattern, text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _create_section(
        self,
        section_num: str,
        title: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a standardized section dictionary."""
        doc_type = self.doc_type_override or self._infer_doc_type(text)
        section = {
            "doc_id": f"{self.base_doc_id}_v{self.version_str}",
            "base_doc_id": self.base_doc_id,
            "version": self.version_str,
            "version_tuple": self.version_tuple,
            "section": section_num,
            "title": title.strip(),
            "text": clean_text(text),
            "tags": [],
            "doc_type": doc_type,
            "file_path": self.full_path,
            "file_name": self.file_path,
            "source": self.full_path,
            "has_table": bool(metadata and metadata.get("table_data")),
            "metadata": metadata
            or {"source": self.full_path, "parser": self.__class__.__name__},
        }
        return section

    def _extract_table_context(self, table_data) -> Dict[str, Any]:
        """Extract semantic context from table data for better tagging."""
        if not table_data:
            return {}

        context = {
            "headers": [],
            "keywords": [],
            "has_numbers": False,
            "has_dates": False,
            "column_count": 0,
            "row_count": len(table_data) if table_data else 0,
        }

        if table_data and len(table_data) > 0:
            if table_data[0]:
                context["headers"] = [str(h).lower() for h in table_data[0]]
                context["column_count"] = len(table_data[0])

            all_text = " ".join(
                " ".join(str(cell) for cell in row) for row in table_data
            )
            context["has_numbers"] = bool(re.search(r"\d+[\.,]?\d*", all_text))
            context["has_dates"] = bool(
                re.search(
                    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}",
                    all_text,
                )
            )

        return context

    def _infer_doc_type(self, text: str) -> str:
        """Infer document type from content."""
        text_lower = text.lower()
        if self._is_form_content(text):
            return "form"
        if any(
            word in text_lower
            for word in ["timecard", "time recording", "travel", "telework"]
        ):
            return "hr_policy"
        if any(
            word in text_lower
            for word in ["procurement", "order request", "basware"]
        ):
            return "procurement"
        if any(
            word in text_lower
            for word in ["policy", "hr", "human resources", "employee", "leave", "benefits"]
        ):
            return "hr_policy"
        if any(
            word in text_lower
            for word in [
                "specification",
                "technical",
                "mil-std",
                "nasa-std",
                "procedure",
                "standard",
            ]
        ):
            return "technical_spec"
        if any(
            word in text_lower
            for word in ["contract", "procurement", "rfp", "rfq", "proposal", "agreement"]
        ):
            return "contract"
        if any(
            word in text_lower
            for word in ["material", "composite", "alloy", "crystal", "structure"]
        ):
            return "technical_spec"
        if any(
            word in text_lower
            for word in ["safety", "compliance", "regulation", "hazard", "risk"]
        ):
            return "safety_compliance"
        return "general"

    def _extract_full_text(self) -> str:
        """Extract full raw text for counting/indexing."""
        return ""

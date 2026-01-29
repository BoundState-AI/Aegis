# boundstate_core/ingestion/parsers/pdf_parser.py
"""
PDF document parser with table extraction and OCR fallback.

Compliance: SWE-033 (Requirements Traceability)
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
"""
from __future__ import annotations

__safety_critical__ = False  # NASA SWE-013

import os
import re
import shutil
import logging
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Optional

from boundstate_core.config.utils import clean_text
from boundstate_core.ingestion.parsers.base import (
    DocumentParser,
    _clean_text,
    _is_mostly_line_junk,
    find_poppler_path,
)

# Optional imports
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

try:
    import pytesseract
    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if not tesseract_cmd:
        candidates = []
        if os.name == "nt":
            program_files = os.environ.get("PROGRAMFILES")
            program_files_x86 = os.environ.get("PROGRAMFILES(X86)")
            for base in filter(None, (program_files, program_files_x86)):
                candidates.append(os.path.join(base, "Tesseract-OCR", "tesseract.exe"))
            candidates.append(
                os.path.join(
                    os.path.expanduser("~"),
                    "AppData",
                    "Local",
                    "Programs",
                    "Tesseract-OCR",
                    "tesseract.exe",
                )
            )
        candidates.append("tesseract")
        for candidate in candidates:
            if candidate == "tesseract" or os.path.exists(candidate):
                tesseract_cmd = candidate
                break
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
except ImportError:
    pytesseract = None

logger = logging.getLogger(__name__)


class PdfParser(DocumentParser):
    """Parser for PDF documents."""

    def parse(self) -> List[Dict[str, Any]]:
        """Parse PDF document."""
        if fitz is None:
            logger.error("PyMuPDF not available. Cannot parse PDF files.")
            return []

        try:
            if self.file_bytes:
                doc = fitz.open(stream=self.file_bytes, filetype="pdf")
            else:
                doc = fitz.open(self.full_path)

            if doc.is_encrypted:
                logger.warning(
                    f"{self.file_path} is encrypted, attempting decryption if possible"
                )

            # Try table-aware extraction first
            all_text = ""
            has_table_structure = False
            used_table_extraction = False
            full_text = ""

            for page_num, page in enumerate(doc):
                blocks = page.get_text("dict")["blocks"]
                rows_by_y: Dict[float, List[Dict]] = {}

                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text = span["text"].strip()
                                if text and not text.isspace():
                                    y_pos = round(span["bbox"][1], 1)
                                    x_pos = span["bbox"][0]

                                    if y_pos not in rows_by_y:
                                        rows_by_y[y_pos] = []

                                    rows_by_y[y_pos].append(
                                        {"x": x_pos, "text": text, "bbox": span["bbox"]}
                                    )

                if rows_by_y:
                    avg_items_per_row = sum(
                        len(items) for items in rows_by_y.values()
                    ) / len(rows_by_y)
                    if avg_items_per_row > 1.5:
                        has_table_structure = True
                        used_table_extraction = True

                page_lines = []
                for y_pos in sorted(rows_by_y.keys()):
                    row_items = sorted(rows_by_y[y_pos], key=lambda item: item["x"])
                    row_text = ""
                    last_x_end = 0

                    for i, item in enumerate(row_items):
                        if i > 0:
                            gap = item["x"] - last_x_end
                            if gap > 50:
                                row_text += " | "
                            else:
                                row_text += " "

                        row_text += item["text"]
                        last_x_end = item["bbox"][2]

                    if row_text:
                        page_lines.append(row_text)

                if page_lines:
                    all_text += "\n".join(page_lines) + "\n\n"
                else:
                    page_text = page.get_text("text")
                    if page_text.strip():
                        cleaned = clean_text(page_text)
                        all_text += page_text + "\n\n"
                        full_text += cleaned + "\n"

            all_text = _clean_text(all_text)
            if _is_mostly_line_junk(all_text):
                logger.warning(
                    f"{self.file_path} appears to be mostly table borders."
                )

            all_text = self._clean_ocr_text(all_text)
            ocr_fallback = False

            header_metadata = self._extract_header_metadata(all_text)
            if header_metadata:
                self.sections.append(
                    self._create_section("0", "Document Header", "", metadata=header_metadata)
                )

            size_counter: Counter = Counter()
            all_spans = []

            for page in doc:
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                size = round(span["size"], 2)
                                text = span["text"].strip()
                                if text:
                                    size_counter[size] += len(text)
                                    all_spans.append(span)

            if not all_text.strip():
                logger.warning(f"No text found in PDF {self.file_path}")
                if convert_from_path is None or pytesseract is None:
                    logger.error(
                        "pdf2image or pytesseract not available for OCR fallback."
                    )
                    return []
                logger.info(f"Attempting OCR fallback for {self.file_path}")
                ocr_fallback = True
                all_text = all_text or ""
                try:
                    poppler_path = find_poppler_path()
                    if poppler_path:
                        images = convert_from_path(
                            self.full_path, dpi=300, poppler_path=poppler_path
                        )
                    else:
                        images = convert_from_path(self.full_path, dpi=300)
                    custom_config = r"--oem 3 --psm 6 -c preserve_interword_spaces=1"
                    for img in images:
                        page_text = pytesseract.image_to_string(
                            img, lang="eng", config=custom_config
                        )
                        all_text += self._clean_ocr_text(page_text) + "\n\n"
                    if not all_text.strip():
                        logger.warning(f"OCR extracted no text from {self.file_path}")
                        return []
                    lines = all_text.split("\n")
                    for line in lines:
                        if line.strip():
                            all_spans.append(
                                {"size": 12.0, "flags": 0, "text": line.strip()}
                            )
                    size_counter[12.0] = len(all_text)
                    used_table_extraction = True
                except Exception as ocr_e:
                    logger.error(f"OCR fallback failed for {self.file_path}: {ocr_e}")
                    return []

            body_size = size_counter.most_common(1)[0][0] if size_counter else 12.0
            heading_sizes = sorted(
                {sz for sz in size_counter if sz > body_size}, reverse=True
            )
            heading_levels = {sz: i + 1 for i, sz in enumerate(heading_sizes)}

            section_stack = [0] * (len(heading_levels) + 1)
            current_title = "Introduction"
            text = ""
            form_pattern = re.compile(r"(\d+\.\d+\s+[^?\n]+?\?)", re.MULTILINE)
            score_pattern = re.compile(
                r"^(Overall Section Score:.*?(?:Acceptable|Not Acceptable))", re.MULTILINE
            )

            for span in all_spans:
                size = round(span["size"], 2)
                flags = span["flags"]
                is_bold = bool(flags & 2**4)
                txt = span["text"].strip()

                if txt:
                    score_match = score_pattern.match(txt)
                    if score_match:
                        if text.strip():
                            level = 1
                            sec_num = ".".join(map(str, section_stack[1 : level + 1]))
                            section = self._create_section(sec_num, current_title, text)
                            if self._is_form_content(text):
                                section["doc_type"] = "form"
                                section["tags"] = section.get("tags", []) + ["form"]
                            self.sections.append(section)
                        section_stack[1] += 1
                        current_title = score_match.group(1).strip()
                        text = ""
                    elif size in heading_levels and is_bold and len(txt) < 200:
                        if text.strip():
                            level = heading_levels.get(size, 1)
                            sec_num = ".".join(map(str, section_stack[1 : level + 1]))
                            section = self._create_section(sec_num, current_title, text)
                            if self._is_form_content(text):
                                section["doc_type"] = "form"
                                section["tags"] = section.get("tags", []) + ["form"]
                            self.sections.append(section)
                        level = heading_levels[size]
                        section_stack[level] += 1
                        for deeper in range(level + 1, len(section_stack)):
                            section_stack[deeper] = 0
                        current_title = txt
                        text = ""
                    else:
                        text += txt + " "

            if text.strip():
                sec_num = ".".join(map(str, section_stack[1:]))
                if sec_num:
                    section = self._create_section(sec_num, current_title, text)
                    if self._is_form_content(text):
                        section["doc_type"] = "form"
                        section["tags"] = section.get("tags", []) + ["form"]
                    self.sections.append(section)

            if not self.sections and all_text.strip():
                section = self._create_section("1", "Document Content", all_text)
                if self._is_form_content(all_text):
                    section["doc_type"] = "form"
                    section["tags"] = section.get("tags", []) + ["form"]
                self.sections.append(section)

            # Chunking fallback for table-heavy documents
            if (
                len(self.sections) < max(1, len(all_text) // 1000)
                and used_table_extraction
            ):
                logger.info(
                    f"Falling back to chunking for {self.file_path}"
                )
                self.sections = []
                text_parts = re.split(r"\n\n+|\n(?=\d+\.\d+\s)", all_text.strip())
                current_chunk: List[str] = []
                current_size = 0
                chunk_num = 1
                target_chunk_size = 200

                for part in text_parts:
                    part = part.strip()
                    if not part:
                        continue
                    part_size = len(part)

                    if part_size > 400:
                        sentences = re.split(r"(?<=[.!?])\s+|(?<=[;:])\s+", part)
                        for sentence in sentences:
                            if (
                                current_size + len(sentence) > target_chunk_size
                                and current_chunk
                            ):
                                chunk_text = " ".join(current_chunk)
                                title = self._extract_title_from_chunk(
                                    chunk_text, chunk_num
                                )
                                self.sections.append(
                                    self._create_section(str(chunk_num), title, chunk_text)
                                )
                                chunk_num += 1
                                current_chunk = [sentence]
                                current_size = len(sentence)
                            else:
                                current_chunk.append(sentence)
                                current_size += len(sentence)
                    elif current_size + part_size > target_chunk_size and current_chunk:
                        chunk_text = " ".join(current_chunk)
                        title = self._extract_title_from_chunk(chunk_text, chunk_num)
                        self.sections.append(
                            self._create_section(str(chunk_num), title, chunk_text)
                        )
                        chunk_num += 1
                        current_chunk = [part]
                        current_size = part_size
                    else:
                        current_chunk.append(part)
                        current_size += part_size

                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    title = self._extract_title_from_chunk(chunk_text, chunk_num)
                    self.sections.append(
                        self._create_section(str(chunk_num), title, chunk_text)
                    )

            # Split into sentences
            final_sections = []
            for section in self.sections:
                if section["doc_type"] != "form" or "question" not in section["tags"]:
                    sentences = self._split_sentences(section["text"])
                    for i, sentence in enumerate(sentences, 1):
                        if len(sentence.split()) > 5:
                            final_sections.append(
                                self._create_section(
                                    f"{section['section']}.{i}",
                                    f"{section['title']} Part {i}",
                                    sentence,
                                )
                            )
                            final_sections[-1]["doc_type"] = section["doc_type"]
                            final_sections[-1]["tags"] = section["tags"]
                else:
                    final_sections.append(section)
            self.sections = final_sections

            if self.sections:
                self.sections[-1]["full_text"] = full_text

            try:
                doc.close()
            except Exception:
                pass

            logger.info(f"Parsed PDF {self.file_path}: {len(self.sections)} sections")
            return self.sections

        except Exception as e:
            logger.error(f"Error parsing PDF {self.file_path}: {e}")
            return []

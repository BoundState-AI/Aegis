#!/usr/bin/env python3
"""
Content extraction for HTML/PDF sources.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Optional


@dataclass
class ExtractedText:
    text: str
    extraction_method: str
    content_type: str


def _decode_bytes(raw_content: bytes) -> str:
    if not raw_content:
        return ""
    for encoding in ("utf-8", "latin-1"):
        try:
            return raw_content.decode(encoding)
        except Exception:
            continue
    return raw_content.decode("utf-8", errors="ignore")


def _extract_html_bs4(raw_content: bytes) -> Optional[ExtractedText]:
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return None

    html = _decode_bytes(raw_content)
    soup = BeautifulSoup(html, "html.parser")

    for selector in ("script", "style", "noscript", "nav", "footer", "header", "aside", "form", "svg"):
        for node in soup.select(selector):
            node.decompose()

    main_candidates = (
        soup.select_one("main")
        or soup.select_one("article")
        or soup.select_one("div.content")
        or soup.select_one("div#content")
        or soup.body
        or soup
    )
    text = main_candidates.get_text("\n", strip=True) if main_candidates else ""
    return ExtractedText(text=text, extraction_method="html_bs4", content_type="text/html")


def _extract_html_regex(raw_content: bytes) -> ExtractedText:
    html = _decode_bytes(raw_content)
    html = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    text = re.sub(r"\s+", " ", html).strip()
    return ExtractedText(text=text, extraction_method="html_regex", content_type="text/html")


def _extract_pdf(raw_content: bytes) -> Optional[ExtractedText]:
    try:
        import fitz  # pymupdf
    except Exception:
        return None

    if not raw_content:
        return ExtractedText(text="", extraction_method="pdf_pymupdf", content_type="application/pdf")

    doc = fitz.open(stream=BytesIO(raw_content), filetype="pdf")
    chunks = []
    for page in doc:
        chunks.append(page.get_text("text"))
    text = "\n".join(chunks)
    return ExtractedText(text=text, extraction_method="pdf_pymupdf", content_type="application/pdf")


def extract_text(raw_content: bytes, *, url: str, content_type: str = "") -> ExtractedText:
    """
    Extract readable text from raw response bytes.
    """
    lowered = (content_type or "").lower()
    is_pdf = ".pdf" in url.lower() or "application/pdf" in lowered
    if is_pdf:
        pdf_result = _extract_pdf(raw_content)
        if pdf_result is not None:
            return pdf_result
        fallback = _decode_bytes(raw_content)
        return ExtractedText(
            text=fallback,
            extraction_method="pdf_fallback_decode",
            content_type="application/pdf",
        )

    bs4_result = _extract_html_bs4(raw_content)
    if bs4_result is not None:
        return bs4_result

    if "html" in lowered or "<html" in _decode_bytes(raw_content)[:200].lower():
        return _extract_html_regex(raw_content)

    return ExtractedText(
        text=_decode_bytes(raw_content),
        extraction_method="raw_decode",
        content_type=content_type or "application/octet-stream",
    )

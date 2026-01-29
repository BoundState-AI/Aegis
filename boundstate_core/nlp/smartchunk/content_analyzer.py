import re
from dataclasses import dataclass, field
from typing import Pattern, Dict, List, Any

class ContentAnalyzer:
    """Deep content analysis for strategy refinement."""
    
    def __init__(self):
        # Compiled patterns for performance
        self.STANDARD_PATTERNS: Dict[str, Pattern] = {
            "astm": re.compile(r"ASTM\\s+[A-Z]\\d{2,4}", re.IGNORECASE),
            "iso": re.compile(r"ISO[\\s-]?\\d{3,5}", re.IGNORECASE),
            "mil": re.compile(r"MIL-[A-Z]+-\\d+", re.IGNORECASE),
            "nasa": re.compile(r"NASA-STD-\\d{4}", re.IGNORECASE),
            "sae": re.compile(r"SAE\\s+[AJ]\\d{3,4}", re.IGNORECASE),
        }
        self.TOC_PATTERNS: Dict[str, Pattern] = {
            "numbered": re.compile(r"^\\s*\\d+\\.[\\d\\.]*\\s+[A-Z]", re.MULTILINE),
            "toc_header": re.compile(r"table\\s+of\\s+contents", re.IGNORECASE),
            "section": re.compile(r"^(Section|Chapter|Part)\\s+\\d+", re.MULTILINE),
        }
        self.REQUIREMENT_PATTERNS: Dict[str, Pattern] = {
            "shall": re.compile(r"\\bshall\\b", re.IGNORECASE),
            "must": re.compile(r"\\bmust\\b", re.IGNORECASE),
            "req_id": re.compile(r"(REQ|SWE|SPEC)-\\d{3,4}"),
        }

    def analyze_sample(self, sample: bytes, deep_scan: bool = True) -> dict:
        """Perform deep content analysis on sample."""
        text = sample.decode("utf-8", errors="ignore")
        results = {
            "standards_detected": [],
            "has_toc": False,
            "has_numbered_sections": False,
            "requirement_density": 0.0,
            "table_indicators": 0,
            "formula_indicators": 0,
            "is_test_report": False,
        }
        if not deep_scan:
            results["has_toc"] = "contents" in text.lower()
            results["table_indicators"] = text.count("Table ")
            return results
        for name, pattern in self.STANDARD_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                results["standards_detected"].extend(matches[:5])
        results["has_toc"] = bool(self.TOC_PATTERNS["toc_header"].search(text))
        results["has_numbered_sections"] = bool(self.TOC_PATTERNS["numbered"].search(text))
        shall_count = len(self.REQUIREMENT_PATTERNS["shall"].findall(text))
        must_count = len(self.REQUIREMENT_PATTERNS["must"].findall(text))
        results["requirement_density"] = (shall_count + must_count) / (len(text) / 1024) if len(text) > 0 else 0.0
        test_indicators = ["test results", "specimen", "tensile", "fatigue", "failure"]
        results["is_test_report"] = sum(1 for ind in test_indicators if ind in text.lower()) >= 3
        return results

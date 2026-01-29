"""Minimal werkzeug.utils module.

Provides secure_filename for tests.

Compliance: SWE-032 (Data validation)
"""

from __future__ import annotations

import re

__all__ = ["secure_filename"]
__safety_critical__ = False

def secure_filename(filename: str) -> str:
    """Sanitize filenames by removing unsafe characters. Compliance: SWE-032."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", filename).strip("._")
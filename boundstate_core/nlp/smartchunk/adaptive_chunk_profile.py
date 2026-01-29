from typing import Any, Dict, List
from pydantic import BaseModel, Field
from copy import deepcopy

class ChunkProfile(BaseModel):
    chunk_size: int = 1024
    overlap: int = 128
    section_detection: bool = True
    rationale: List[str] = Field(default_factory=list)

class AdaptiveChunkProfile(BaseModel):
    base_profile: ChunkProfile
    adjustments: Dict[str, Any] = Field(default_factory=dict)
    adjustment_rationale: List[str] = Field(default_factory=list)

    def adapt(self, analysis_results: dict) -> ChunkProfile:
        profile = deepcopy(self.base_profile)
        rationale = []
        # Example: adjust chunk size for high requirement density
        if analysis_results.get("requirement_density", 0) > 2.0:
            profile.chunk_size = 512
            rationale.append("High requirement density: using smaller chunks.")
        if analysis_results.get("is_test_report"):
            profile.section_detection = False
            rationale.append("Test report detected: disabling section detection.")
        if analysis_results.get("has_toc"):
            profile.overlap = 64
            rationale.append("TOC detected: reducing overlap.")
        profile.rationale = rationale
        return profile

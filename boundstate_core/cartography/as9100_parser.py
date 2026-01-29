# Copyright 2025 BoundStateAI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
BoundState AS9100 Document Parser and Learning System
Compliance: SWE-013, SWE-033

Parses AS9100 PDF/DOCX and learns requirement patterns.
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
import fitz  # PyMuPDF for PDF parsing

from ..parsers import DocumentParser, PdfParser, DocxParser
from boundstate_core.nlp.phrase_extractor import PhraseExtractor, ExtractedPhrases
from boundstate_core.nlp.content_miner import ContentMiner

logger = logging.getLogger(__name__)

__all__ = ["AS9100Parser", "AS9100Clause", "AS9100LearningSystem", "parse_as9100_file"]


@dataclass
class AS9100Requirement:
    """Single requirement from AS9100."""
    text: str
    clause_id: str
    type: str  # 'shall', 'should', 'may'
    keywords: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)


class AS9100Clause(BaseModel):
    """Enhanced AS9100 clause with full parsing."""
    
    id: str = Field(description="Clause number (e.g., '8.4')")
    title: str = Field(description="Clause title")
    full_text: str = Field(description="Complete clause text")
    requirements: List[AS9100Requirement] = Field(default_factory=list)
    rake_keywords: List[Tuple[str, float]] = Field(default_factory=list)
    noun_phrases: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list, description="Referenced standards/clauses")
    sub_clauses: Dict[str, 'AS9100Clause'] = Field(default_factory=dict)
    parent_clause: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    model_config = {"extra": "forbid", "populate_by_name": True}


class AS9100Parser:
    """
    Parses AS9100 Rev D from PDF or DOCX format.
    
    Handles:
    - Multi-level clause structure (4, 4.1, 4.1.1, etc.)
    - Requirement extraction (shall/should/may)
    - Cross-references between clauses
    - Annex and appendix content
    """
    
    def __init__(self):
        self.phrase_extractor = PhraseExtractor()
        self.content_miner = ContentMiner()
        self.clauses: Dict[str, AS9100Clause] = {}
        self.requirements: List[AS9100Requirement] = []
        
    def parse_file(self, file_path: str) -> Dict[str, AS9100Clause]:
        """
        Parse AS9100 from PDF or DOCX file.
        
        Args:
            file_path: Path to AS9100 Rev D document
            
        Returns:
            Dictionary of clause_id -> AS9100Clause
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"AS9100 file not found: {file_path}")
            
        logger.info(f"Parsing AS9100 from: {file_path}")
        
        # Extract text based on file type
        if file_path.suffix.lower() == '.pdf':
            text = self._parse_pdf(file_path)
        elif file_path.suffix.lower() == '.docx':
            text = self._parse_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
            
        # Parse the extracted text
        self._parse_text(text)
        
        # Build clause hierarchy
        self._build_hierarchy()
        
        # Extract requirements
        self._extract_requirements()
        
        # Analyze with ContentMiner for references
        self._analyze_references()
        
        logger.info(f"Parsed {len(self.clauses)} clauses with {len(self.requirements)} requirements")
        
        return self.clauses
    
    def _parse_pdf(self, file_path: Path) -> str:
        """Extract text from PDF maintaining structure."""
        text_parts = []
        
        with fitz.open(file_path) as pdf:
            for page_num, page in enumerate(pdf):
                # Get structured text
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            line_text = ""
                            for span in line["spans"]:
                                line_text += span["text"]
                            
                            if line_text.strip():
                                text_parts.append(line_text.strip())
                                
        return "\n".join(text_parts)
    
    def _parse_docx(self, file_path: Path) -> str:
        """Extract text from DOCX maintaining structure."""
        parser = DocxParser(str(file_path))
        sections = parser.parse()
        
        # Reconstruct with section numbers
        text_parts = []
        for section in sections:
            if section['section'] and section['title']:
                text_parts.append(f"{section['section']} {section['title']}")
            text_parts.append(section['text'])
            
        return "\n\n".join(text_parts)
    
    def _parse_text(self, text: str):
        """Parse AS9100 text into clauses."""
        # Enhanced pattern for multi-level clauses
        clause_patterns = [
            # Main clauses (4 Quality management system)
            re.compile(r'^(\d+)\s+([^\n]+)$', re.MULTILINE),
            # Sub-clauses (4.1 Understanding the organization)
            re.compile(r'^(\d+\.\d+)\s+([^\n]+)$', re.MULTILINE),
            # Sub-sub-clauses (4.1.1 Specific requirement)
            re.compile(r'^(\d+\.\d+\.\d+)\s+([^\n]+)$', re.MULTILINE),
            # Letter sub-clauses (8.5.1.1 a) Configuration management)
            re.compile(r'^([a-z]\))\s+([^\n]+)$', re.MULTILINE)
        ]
        
        # Find all clause headers
        all_matches = []
        for pattern in clause_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                all_matches.append({
                    'pos': match.start(),
                    'id': match.group(1),
                    'title': match.group(2).strip(),
                    'end': match.end()
                })
                
        # Sort by position
        all_matches.sort(key=lambda x: x['pos'])
        
        # Extract clause content
        for i, match in enumerate(all_matches):
            clause_id = match['id']
            clause_title = match['title']
            
            # Get content until next clause
            start = match['end']
            end = all_matches[i + 1]['pos'] if i + 1 < len(all_matches) else len(text)
            content = text[start:end].strip()
            
            if not content:
                continue
                
            # Extract phrases
            phrases = self.phrase_extractor.extract(
                content,
                source=f"AS9100 {clause_id}"
            )
            
            # Create clause
            clause = AS9100Clause(
                id=clause_id,
                title=clause_title,
                full_text=content,
                rake_keywords=phrases.rake_keywords[:20],
                noun_phrases=phrases.noun_phrases[:15],
                confidence=phrases.confidence
            )
            
            self.clauses[clause_id] = clause
    
    def _build_hierarchy(self):
        """Build parent-child relationships between clauses."""
        for clause_id, clause in self.clauses.items():
            # Find parent (4.1.1 -> parent is 4.1)
            parts = clause_id.split('.')
            if len(parts) > 1:
                parent_id = '.'.join(parts[:-1])
                if parent_id in self.clauses:
                    clause.parent_clause = parent_id
                    self.clauses[parent_id].sub_clauses[clause_id] = clause
    
    def _extract_requirements(self):
        """Extract SHALL/SHOULD/MAY requirements."""
        requirement_patterns = [
            (r'([^.]*\bshall\b[^.]*\.)', 'shall'),
            (r'([^.]*\bshould\b[^.]*\.)', 'should'),
            (r'([^.]*\bmust\b[^.]*\.)', 'shall'),  # Treat 'must' as 'shall'
            (r'([^.]*\bmay\b[^.]*\.)', 'may')
        ]
        
        for clause_id, clause in self.clauses.items():
            for pattern, req_type in requirement_patterns:
                matches = re.finditer(pattern, clause.full_text, re.IGNORECASE)
                
                for match in matches:
                    req_text = match.group(1).strip()
                    
                    # Extract key phrases from requirement
                    req_phrases = self.phrase_extractor.extract(
                        req_text,
                        rake_max_length=3
                    )
                    
                    requirement = AS9100Requirement(
                        text=req_text,
                        clause_id=clause_id,
                        type=req_type,
                        keywords=[kw for kw, _ in req_phrases.rake_keywords[:5]]
                    )
                    
                    clause.requirements.append(requirement)
                    self.requirements.append(requirement)
    
    def _analyze_references(self):
        """Extract references to other standards and clauses."""
        for clause_id, clause in self.clauses.items():
            # Mine content for references
            content_result = self.content_miner.mine_content(clause.full_text)
            
            # Add references
            for ref in content_result.references:
                clause.references.append(ref['id'])
                
            # Find internal clause references (e.g., "see 8.4.1")
            internal_refs = re.findall(r'(?:see|refer to|per)\s+(\d+(?:\.\d+)*)', 
                                     clause.full_text, re.IGNORECASE)
            clause.references.extend(internal_refs)


class AS9100LearningSystem:
    """
    Learns patterns from AS9100 to improve document classification.
    
    Features:
    - Learns requirement language patterns
    - Builds clause-to-topic mappings
    - Creates compliance templates
    """
    
    def __init__(self, as9100_clauses: Dict[str, AS9100Clause]):
        self.clauses = as9100_clauses
        self.requirement_patterns: Dict[str, List[str]] = {
            'shall': [],
            'should': [],
            'may': []
        }
        self.topic_mappings: Dict[str, List[str]] = {}
        self.learned_templates: Dict[str, str] = {}
        
    def learn_patterns(self):
        """Learn language patterns from AS9100."""
        logger.info("Learning patterns from AS9100...")
        
        # Learn requirement patterns
        self._learn_requirement_patterns()
        
        # Learn topic mappings
        self._learn_topic_mappings()
        
        # Generate compliance templates
        self._generate_templates()
        
        return {
            'requirement_patterns': self.requirement_patterns,
            'topic_mappings': self.topic_mappings,
            'templates': self.learned_templates
        }
    
    def _learn_requirement_patterns(self):
        """Extract common patterns in requirements."""
        for clause in self.clauses.values():
            for req in clause.requirements:
                # Extract pattern around requirement type
                pattern = self._extract_pattern(req.text, req.type)
                if pattern:
                    self.requirement_patterns[req.type].append(pattern)
    
    def _extract_pattern(self, text: str, req_type: str) -> Optional[str]:
        """Extract reusable pattern from requirement text."""
        # Replace specific nouns with placeholders
        pattern = text.lower()
        
        # Common noun replacements
        replacements = [
            (r'\b(?:organization|company)\b', '[ENTITY]'),
            (r'\b(?:product|service)\b', '[DELIVERABLE]'),
            (r'\b(?:customer|client)\b', '[CUSTOMER]'),
            (r'\b(?:process|procedure)\b', '[PROCESS]'),
            (r'\b(?:requirement|specification)\b', '[REQUIREMENT]')
        ]
        
        for old, new in replacements:
            pattern = re.sub(old, new, pattern)
            
        return pattern if '[' in pattern else None
    
    def _learn_topic_mappings(self):
        """Map clauses to topics based on keywords."""
        topic_keywords = {
            'management': ['management', 'leadership', 'planning', 'policy'],
            'risk': ['risk', 'opportunity', 'assessment', 'mitigation'],
            'design': ['design', 'development', 'verification', 'validation'],
            'production': ['production', 'manufacturing', 'control', 'monitoring'],
            'purchasing': ['purchasing', 'supplier', 'procurement', 'vendor'],
            'nonconformity': ['nonconformity', 'corrective', 'preventive', 'action']
        }
        
        for clause_id, clause in self.clauses.items():
            clause_text = clause.full_text.lower()
            
            for topic, keywords in topic_keywords.items():
                score = sum(1 for kw in keywords if kw in clause_text)
                
                if score >= 2:  # At least 2 keywords match
                    if topic not in self.topic_mappings:
                        self.topic_mappings[topic] = []
                    self.topic_mappings[topic].append(clause_id)
    
    def _generate_templates(self):
        """Generate document templates based on AS9100 patterns."""
        # Template for procedures
        procedure_clauses = []
        for clause in self.clauses.values():
            if 'procedure' in clause.full_text.lower():
                procedure_clauses.append(clause)
                
        if procedure_clauses:
            self.learned_templates['procedure'] = self._create_procedure_template(procedure_clauses)
            
    def _create_procedure_template(self, clauses: List[AS9100Clause]) -> str:
        """Create a procedure template from AS9100 patterns."""
        template = """# [PROCEDURE TITLE]

## 1. Purpose
This procedure establishes the requirements for [PROCESS].

## 2. Scope  
This procedure applies to [SCOPE].

## 3. Requirements
"""
        
        # Add common requirements
        common_reqs = set()
        for clause in clauses:
            for req in clause.requirements:
                if req.type == 'shall':
                    common_reqs.add(self._generalize_requirement(req.text))
                    
        for i, req in enumerate(common_reqs, 1):
            template += f"3.{i} The organization shall {req}\n"
            
        return template
    
    def _generalize_requirement(self, req_text: str) -> str:
        """Generalize a requirement for reuse."""
        # Remove specific clause references
        generalized = re.sub(r'\b\d+\.\d+(?:\.\d+)?\b', '[REFERENCE]', req_text)
        
        # Remove 'shall' as we'll add it back
        generalized = re.sub(r'\bshall\b', '', generalized, flags=re.IGNORECASE)
        
        return generalized.strip()


def parse_as9100_file(file_path: str) -> Tuple[Dict[str, AS9100Clause], Dict[str, Any]]:
    """
    Parse AS9100 file and learn patterns.
    
    Args:
        file_path: Path to AS9100 Rev D document
        
    Returns:
        Tuple of (clauses dict, learned patterns dict)
    """
    # Parse the document
    parser = AS9100Parser()
    clauses = parser.parse_file(file_path)
    
    # Learn from it
    learner = AS9100LearningSystem(clauses)
    patterns = learner.learn_patterns()
    
    return clauses, patterns
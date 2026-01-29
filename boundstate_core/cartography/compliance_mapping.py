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
BoundState AS9100 Compliance Mapper
Maps your documents to AS9100 requirements.
"""

from __future__ import annotations

import json
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

from boundstate_core.cartography.as9100_parser import AS9100Parser, AS9100Clause
from boundstate_core.nlp.phrase_extractor import calculate_semantic_overlap, ExtractedPhrases
from boundstate_core.cartography.graph_builder import GraphBuilder


class AS9100Analyzer:
    """Wrapper class for AS9100Parser to provide compliance analysis functionality."""
    
    def __init__(self):
        self.parser = AS9100Parser()
        self.clauses: List[AS9100Clause] = []
        self.clause_map: Dict[str, AS9100Clause] = {}
        self.version = "AS9100 Rev D"
        
    def load_standard(self, as9100_text: str) -> None:
        """Load AS9100 standard from text content."""
        # Parse the text to extract clauses
        self.parser._parse_text(as9100_text)
        self.parser._build_hierarchy()
        self.parser._extract_requirements()
        
        # Convert parser clauses to list format
        self.clauses = list(self.parser.clauses.values())
        self.clause_map = self.parser.clauses
        
    def find_requirements(self, clause_id: str) -> List[Dict[str, Any]]:
        """Find all requirements for a specific clause."""
        requirements = []
        for req in self.parser.requirements:
            if req.clause_id == clause_id:
                requirements.append({
                    "text": req.text,
                    "type": req.type,
                    "keywords": req.keywords
                })
        return requirements


class ComplianceMapper:
    """Maps documents to AS9100 clauses for compliance tracking."""
    
    def __init__(self, as9100_text: Optional[str] = None):
        self.analyzer = AS9100Analyzer()
        if as9100_text:
            self.analyzer.load_standard(as9100_text)
            
    def map_documents_to_clauses(
        self,
        document_phrases: Dict[str, ExtractedPhrases],
        min_overlap: float = 0.3
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Map each document to relevant AS9100 clauses.
        
        Returns:
            Dict of doc_id -> [(clause_id, overlap_score), ...]
        """
        mappings = {}
        
        for doc_id, doc_phrases in document_phrases.items():
            clause_matches = []
            
            for clause in self.analyzer.clauses:
                # Create ExtractedPhrases for clause
                # Extract keywords from rake_keywords tuples
                keywords = [kw[0] for kw in clause.rake_keywords] if clause.rake_keywords else []
                
                clause_phrases = ExtractedPhrases(
                    rake_keywords=keywords,
                    noun_phrases=clause.noun_phrases,
                    confidence=clause.confidence,
                    source="AS9100",
                    technical_terms=[],
                    compliance_refs=[]
                )
                
                # Calculate overlap
                overlap = calculate_semantic_overlap(
                    doc_phrases,
                    clause_phrases,
                    min_overlap=min_overlap
                )
                
                if overlap["is_significant"]:
                    clause_matches.append((clause.id, overlap["overlap_ratio"]))
            
            if clause_matches:
                # Sort by overlap score
                clause_matches.sort(key=lambda x: x[1], reverse=True)
                mappings[doc_id] = clause_matches[:5]  # Top 5 matches
                
        return mappings
    
    def generate_compliance_report(
        self,
        mappings: Dict[str, List[Tuple[str, float]]],
        graph_builder: GraphBuilder
    ) -> Dict[str, Any]:
        """Generate AS9100 compliance coverage report."""
        
        # Find which clauses are covered
        covered_clauses = set()
        for doc_id, clause_matches in mappings.items():
            for clause_id, _ in clause_matches:
                covered_clauses.add(clause_id)
        
        # Find gaps
        all_clauses = set(clause.id for clause in self.analyzer.clauses)
        gap_clauses = all_clauses - covered_clauses
        
        # Find high-risk gaps (clauses with many requirements)
        high_risk_gaps = []
        for clause_id in gap_clauses:
            requirements = self.analyzer.find_requirements(clause_id)
            if len(requirements) > 2:
                clause = self.analyzer.clause_map.get(clause_id)
                if clause:
                    high_risk_gaps.append({
                        "clause_id": clause_id,
                        "title": clause.title,
                        "requirement_count": len(requirements)
                    })
        
        # Build report
        report = {
            "summary": {
                "total_clauses": len(all_clauses),
                "covered_clauses": len(covered_clauses),
                "coverage_percentage": len(covered_clauses) / len(all_clauses) * 100,
                "gap_count": len(gap_clauses)
            },
            "covered_clauses": list(covered_clauses),
            "gap_clauses": list(gap_clauses),
            "high_risk_gaps": high_risk_gaps,
            "document_mappings": mappings
        }
        
        return report
    
    def generate_compliance_matrix(
        self,
        mappings: Dict[str, List[Tuple[str, float]]],
        graph_builder: GraphBuilder
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate a compliance matrix showing clause coverage.
        
        Returns:
            Dict of clause_id -> {
                'title': str,
                'documents': List[str],
                'coverage_score': float,
                'requirement_count': int
            }
        """
        matrix = {}
        
        # Initialize matrix with all clauses
        for clause in self.analyzer.clauses:
            matrix[clause.id] = {
                'title': clause.title,
                'documents': [],
                'coverage_score': 0.0,
                'requirement_count': len(self.analyzer.find_requirements(clause.id))
            }
        
        # Fill in document mappings
        for doc_id, clause_matches in mappings.items():
            for clause_id, overlap_score in clause_matches:
                if clause_id in matrix:
                    matrix[clause_id]['documents'].append(doc_id)
                    # Update coverage score (max of all document scores)
                    matrix[clause_id]['coverage_score'] = max(
                        matrix[clause_id]['coverage_score'],
                        overlap_score
                    )
        
        # Add graph-based insights if available
        if graph_builder and graph_builder.nodes:
            for clause_id, clause_info in matrix.items():
                # Check if mapped documents are authoritative
                authoritative_docs = []
                for doc_id in clause_info['documents']:
                    if doc_id in graph_builder.nodes:
                        node = graph_builder.nodes[doc_id]
                        # Check if document is highly referenced (hub)
                        out_degree = graph_builder.graph.out_degree(doc_id)
                        in_degree = graph_builder.graph.in_degree(doc_id)
                        if in_degree > 2 or out_degree > 3:
                            authoritative_docs.append(doc_id)
                
                clause_info['authoritative_documents'] = authoritative_docs
        
        return matrix
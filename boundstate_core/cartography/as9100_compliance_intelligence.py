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
AS9100 Rev D Compliance Intelligence System - Enhanced
Real-time AI-driven compliance for aerospace and defense
Compliance: SWE-013, SWE-033
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, field_validator

# Configure logging
logger = logging.getLogger(__name__)

__all__ = [
    "AS9100ComplianceIntelligence",
    "ComplianceMapping",
    "AuditResponse",
    "ComplianceSnapshot",
    "create_audit_dashboard_data"
]

__safety_critical__ = True  # Compliance tracking is safety-critical


class ComplianceMapping(BaseModel):
    """Document to AS9100 clause mapping result."""
    
    mapped_documents: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Documents mapped to AS9100 clauses"
    )
    coverage_by_clause: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="AS9100 clauses and their implementing documents"
    )
    gaps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Identified compliance gaps"
    )
    statistics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Coverage statistics"
    )
    
    model_config = {"extra": "forbid", "populate_by_name": True}


class AuditResponse(BaseModel):
    """Response for audit evidence request."""
    
    clause: str = Field(description="AS9100 clause reference")
    requirement_summary: str = Field(description="Clause requirement text")
    implementing_documents: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Documents implementing this clause"
    )
    evidence: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Evidence snippets with scores"
    )
    compliance_status: str = Field(
        default="NOT DETERMINED",
        description="Compliance status for clause"
    )
    explanation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Explanation of mapping rationale"
    )
    
    model_config = {"extra": "forbid", "populate_by_name": True}


class ComplianceSnapshot(BaseModel):
    """Live compliance status snapshot."""
    
    compliant: float = Field(ge=0, le=100, description="Percentage fully compliant")
    partial: float = Field(ge=0, le=100, description="Percentage partially compliant")
    gaps: float = Field(ge=0, le=100, description="Percentage with gaps")
    high_risk_gaps: int = Field(ge=0, description="Number of high-risk gaps")
    last_updated: datetime = Field(default_factory=datetime.now)
    weighted_score: float = Field(
        ge=0, le=100,
        description="Weighted compliance score considering criticality"
    )
    
    model_config = {"extra": "forbid", "populate_by_name": True}


class AS9100ComplianceIntelligence:
    """Living AS9100D compliance system with enhanced audit capabilities."""
    
    # Critical clauses get 1.5x weight
    CRITICAL_CLAUSES = {'4.4', '5.1', '6.1', '7.2', '8.1', '8.4', '8.5', '9.1', '9.2', '10.2'}
    
    # Clause weights for different categories
    CLAUSE_WEIGHTS = {
        'management': 1.5,
        'operational': 1.0,
        'support': 0.8,
        'improvement': 1.2
    }
    
    def __init__(self, index_path: Optional[str] = None):
        """Initialize with optional custom index path."""
        from boundstate_core.storage.index import create_index
        
        self.index = create_index(db_path=index_path) if index_path else create_index()
        self.as9100 = {}
        self.compliance_map = {}
        self.gap_tracker = defaultdict(list)
        self.previous_mappings = []  # For drift detection
        
    def load_as9100_knowledge(self, as9100_path: str = "as9100d_parsed.json"):
        """Load AS9100D as structured, queryable knowledge."""
        logger.info("Loading AS9100D Compliance Intelligence...")
        
        # Load parsed AS9100D
        with open(as9100_path, "r") as f:
            self.as9100 = json.load(f)
            
        # Index each clause for semantic search
        for clause_id, clause in self.as9100['clauses'].items():
            if clause.get('requirements'):
                # Determine clause category for weighting
                category = self._categorize_clause(clause_id)
                
                # Index the clause itself
                self.index.add([{
                    "doc_id": f"AS9100D-{clause_id}",
                    "base_doc_id": "AS9100D",
                    "version": "D",
                    "section": clause_id,
                    "title": f"{clause_id} {clause['title']}",
                    "text": clause['full_text'],
                    "tags": ["as9100", "standard", "requirement", f"clause-{clause_id}", category],
                    "doc_type": "standard",
                    "metadata": {
                        "requirement_count": clause['requirement_count'],
                        "keywords": [kw for kw, _ in clause['rake_keywords'][:10]],
                        "category": category,
                        "is_critical": clause_id in self.CRITICAL_CLAUSES
                    }
                }])
        
        logger.info(f"Loaded {len(self.as9100['clauses'])} AS9100D clauses")
    
    def answer_compliance_question(self, question: str, include_explanation: bool = False) -> Dict:
        """Natural language Q&A about AS9100 requirements with optional explanation."""
        logger.info(f"Processing compliance question: '{question}'")
        
        # Search AS9100 clauses
        results = self.index.search_text(
            question, 
            k=5,
            doc_type='standard',
            base_doc_id='AS9100D'
        )
        
        response = {
            'question': question,
            'answers': [],
            'relevant_clauses': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for result in results:
            clause_id = result['section']
            clause = self.as9100['clauses'].get(clause_id, {})
            
            answer = {
                'clause': f"{clause_id} {clause.get('title', '')}",
                'relevance_score': result['score'],
                'summary': result['text'][:300] + "...",
                'requirements': clause.get('requirements', [])[:3],
                'keywords': result['metadata'].get('keywords', []),
                'is_critical': clause_id in self.CRITICAL_CLAUSES
            }
            
            if include_explanation:
                answer['explanation'] = {
                    'matched_keywords': self._get_matched_keywords(question, clause),
                    'semantic_similarity': result['score'],
                    'clause_category': result['metadata'].get('category', 'unknown')
                }
            
            response['answers'].append(answer)
            response['relevant_clauses'].append(clause_id)
        
        return response
    
    def map_internal_documents(
        self, 
        internal_docs: List[Dict],
        save_for_drift_detection: bool = True
    ) -> ComplianceMapping:
        """Map internal documents to AS9100 clauses with weighted scoring."""
        logger.info(f"Mapping {len(internal_docs)} internal documents to AS9100D requirements...")
        
        mapping_results = ComplianceMapping()
        
        # For each internal document
        for doc in internal_docs:
            doc_id = doc['doc_id']
            doc_text = doc['text'].lower()
            author = doc.get('author', 'Unknown')
            
            # Find which AS9100 clauses this document addresses
            addressed_clauses = []
            
            for clause_id, clause in self.as9100['clauses'].items():
                if self._document_addresses_clause(doc_text, clause):
                    confidence = self._calculate_mapping_confidence(doc_text, clause)
                    
                    addressed_clauses.append({
                        'clause_id': clause_id,
                        'title': clause['title'],
                        'confidence': confidence,
                        'is_critical': clause_id in self.CRITICAL_CLAUSES
                    })
            
            mapping_results.mapped_documents[doc_id] = {
                'title': doc.get('title', doc_id),
                'type': doc.get('doc_type', 'unknown'),
                'author': author,
                'addresses_clauses': addressed_clauses,
                'clause_count': len(addressed_clauses)
            }
            
            # Track coverage by clause with author info
            for clause_info in addressed_clauses:
                clause_id = clause_info['clause_id']
                if clause_id not in mapping_results.coverage_by_clause:
                    mapping_results.coverage_by_clause[clause_id] = []
                
                mapping_results.coverage_by_clause[clause_id].append({
                    'doc_id': doc_id,
                    'doc_title': doc.get('title', doc_id),
                    'author': author,
                    'confidence': clause_info['confidence']
                })
        
        # Identify gaps with severity based on criticality
        for clause_id, clause in self.as9100['clauses'].items():
            if clause['requirement_count'] > 0 and clause_id not in mapping_results.coverage_by_clause:
                severity = 'HIGH' if clause_id in self.CRITICAL_CLAUSES else 'MEDIUM'
                
                mapping_results.gaps.append({
                    'clause': f"{clause_id} {clause['title']}",
                    'requirements': clause['requirement_count'],
                    'severity': severity,
                    'category': self._categorize_clause(clause_id)
                })
        
        # Calculate weighted statistics
        stats = self._calculate_weighted_statistics(mapping_results)
        mapping_results.statistics = stats
        
        # Save for drift detection if requested
        if save_for_drift_detection:
            self.previous_mappings.append({
                'timestamp': datetime.now().isoformat(),
                'mapping': mapping_results.model_dump()
            })
        
        return mapping_results
    
    def generate_audit_response(
        self, 
        clause_id: str, 
        internal_docs: List[Dict],
        include_explanation: bool = True
    ) -> AuditResponse:
        """Generate real-time audit response with explanation."""
        logger.info(f"Generating audit response for clause {clause_id}...")
        
        clause = self.as9100['clauses'].get(clause_id, {})
        if not clause:
            raise ValueError(f'Clause {clause_id} not found')
        
        response = AuditResponse(
            clause=f"{clause_id} {clause['title']}",
            requirement_summary=clause['full_text'][:500] + "..."
        )
        
        # Find implementing documents
        for doc in internal_docs:
            if self._document_addresses_clause(doc['text'].lower(), clause):
                confidence = self._calculate_mapping_confidence(doc['text'].lower(), clause)
                
                response.implementing_documents.append({
                    'doc_id': doc['doc_id'],
                    'title': doc.get('title', doc['doc_id']),
                    'type': doc.get('doc_type', 'unknown'),
                    'author': doc.get('author', 'Unknown'),
                    'confidence': confidence,
                    'link': f"/documents/{doc['doc_id']}"
                })
                
                # Extract scored evidence
                evidence = self._extract_scored_evidence(doc['text'], clause)
                response.evidence.extend(evidence)
        
        # Sort evidence by score
        response.evidence.sort(key=lambda x: x['score'], reverse=True)
        response.evidence = response.evidence[:5]  # Top 5 evidence
        
        # Determine compliance status with weighted consideration
        response.compliance_status = self._determine_compliance_status(
            response.implementing_documents,
            clause_id in self.CRITICAL_CLAUSES
        )
        
        # Add explanation if requested
        if include_explanation:
            response.explanation = self.explain_clause_match(
                clause_id, 
                response.implementing_documents
            )
        
        return response
    
    def explain_clause_match(self, clause_id: str, implementing_docs: List[Dict]) -> Dict:
        """Explain why documents match a specific clause."""
        clause = self.as9100['clauses'].get(clause_id, {})
        
        explanation = {
            'clause_id': clause_id,
            'clause_keywords': [kw for kw, _ in clause.get('rake_keywords', [])[:10]],
            'confidence_breakdown': [],
            'rationale': []
        }
        
        for doc in implementing_docs:
            breakdown = {
                'doc_id': doc['doc_id'],
                'confidence': doc['confidence'],
                'factors': {
                    'explicit_reference': 0.5 if clause_id in doc.get('text', '').lower() else 0.0,
                    'keyword_overlap': min(doc.get('keyword_matches', 0) * 0.05, 0.3),
                    'title_match': 0.2 if clause.get('title', '').lower() in doc.get('text', '').lower() else 0.0
                }
            }
            
            explanation['confidence_breakdown'].append(breakdown)
            
            if doc['confidence'] > 0.8:
                explanation['rationale'].append(f"Strong match: {doc['doc_id']} directly implements requirements")
            elif doc['confidence'] > 0.5:
                explanation['rationale'].append(f"Moderate match: {doc['doc_id']} partially addresses clause")
            else:
                explanation['rationale'].append(f"Weak match: {doc['doc_id']} may need review")
        
        return explanation
    
    def get_compliance_summary(self) -> ComplianceSnapshot:
        """Get live compliance status snapshot."""
        if not hasattr(self, '_last_mapping'):
            return ComplianceSnapshot(
                compliant=0.0,
                partial=0.0,
                gaps=100.0,
                high_risk_gaps=0,
                weighted_score=0.0
            )
        
        mapping = self._last_mapping
        stats = mapping.statistics
        
        # Calculate percentages
        total_clauses = stats['total_as9100_clauses']
        if total_clauses == 0:
            return ComplianceSnapshot()
        
        compliant = len([c for c in mapping.coverage_by_clause.values() 
                        if any(d['confidence'] > 0.8 for d in c)])
        partial = len([c for c in mapping.coverage_by_clause.values() 
                      if all(d['confidence'] <= 0.8 for d in c)])
        gaps = len(mapping.gaps)
        
        return ComplianceSnapshot(
            compliant=(compliant / total_clauses) * 100,
            partial=(partial / total_clauses) * 100,
            gaps=(gaps / total_clauses) * 100,
            high_risk_gaps=stats['high_severity_gaps'],
            weighted_score=stats['weighted_coverage_percentage']
        )
    
    def detect_compliance_drift(self, previous_mapping: Dict) -> Dict:
        """Detect changes in compliance coverage over time."""
        if not self.previous_mappings:
            return {'error': 'No previous mappings available for comparison'}
        
        current = self._last_mapping if hasattr(self, '_last_mapping') else None
        if not current:
            return {'error': 'No current mapping available'}
        
        drift = {
            'timestamp': datetime.now().isoformat(),
            'lost_coverage': [],
            'gained_coverage': [],
            'confidence_changes': [],
            'new_gaps': [],
            'resolved_gaps': []
        }
        
        # Compare clause coverage
        prev_covered = set(previous_mapping.get('coverage_by_clause', {}).keys())
        curr_covered = set(current.coverage_by_clause.keys())
        
        drift['lost_coverage'] = list(prev_covered - curr_covered)
        drift['gained_coverage'] = list(curr_covered - prev_covered)
        
        # Check confidence changes
        for clause_id in prev_covered & curr_covered:
            prev_conf = max(d['confidence'] for d in previous_mapping['coverage_by_clause'][clause_id])
            curr_conf = max(d['confidence'] for d in current.coverage_by_clause[clause_id])
            
            if abs(prev_conf - curr_conf) > 0.1:
                drift['confidence_changes'].append({
                    'clause': clause_id,
                    'previous': prev_conf,
                    'current': curr_conf,
                    'change': curr_conf - prev_conf
                })
        
        # Compare gaps
        prev_gaps = {g['clause'] for g in previous_mapping.get('gaps', [])}
        curr_gaps = {g['clause'] for g in current.gaps}
        
        drift['new_gaps'] = list(curr_gaps - prev_gaps)
        drift['resolved_gaps'] = list(prev_gaps - curr_gaps)
        
        return drift
    
    def _categorize_clause(self, clause_id: str) -> str:
        """Categorize clause for weighting purposes."""
        # AS9100 clause categorization
        if clause_id.startswith(('4', '5')):
            return 'management'
        elif clause_id.startswith(('6', '7', '8')):
            return 'operational'
        elif clause_id.startswith('9'):
            return 'improvement'
        else:
            return 'support'
    
    def _calculate_weighted_statistics(self, mapping: ComplianceMapping) -> Dict:
        """Calculate statistics with criticality weighting."""
        weighted_total = 0.0
        weighted_covered = 0.0
        
        for clause_id, clause in self.as9100['clauses'].items():
            if clause['requirement_count'] > 0:
                # Apply criticality weight
                weight = 1.5 if clause_id in self.CRITICAL_CLAUSES else 1.0
                
                # Apply category weight
                category = self._categorize_clause(clause_id)
                weight *= self.CLAUSE_WEIGHTS.get(category, 1.0)
                
                weighted_total += weight
                
                if clause_id in mapping.coverage_by_clause:
                    # Consider confidence in coverage
                    max_confidence = max(d['confidence'] for d in mapping.coverage_by_clause[clause_id])
                    weighted_covered += weight * max_confidence
        
        # Basic statistics
        total_clauses = sum(1 for c in self.as9100['clauses'].values() if c['requirement_count'] > 0)
        covered_clauses = len(mapping.coverage_by_clause)
        
        return {
            'total_as9100_clauses': total_clauses,
            'covered_clauses': covered_clauses,
            'coverage_percentage': (covered_clauses / total_clauses * 100) if total_clauses > 0 else 0,
            'weighted_coverage_percentage': (weighted_covered / weighted_total * 100) if weighted_total > 0 else 0,
            'total_gaps': len(mapping.gaps),
            'high_severity_gaps': sum(1 for g in mapping.gaps if g['severity'] == 'HIGH'),
            'author_summary': self._summarize_authors(mapping)
        }
    
    def _summarize_authors(self, mapping: ComplianceMapping) -> Dict:
        """Summarize document ownership by author."""
        author_stats = defaultdict(lambda: {'documents': 0, 'clauses_covered': set()})
        
        for doc_id, doc_info in mapping.mapped_documents.items():
            author = doc_info.get('author', 'Unknown')
            author_stats[author]['documents'] += 1
            
            for clause in doc_info['addresses_clauses']:
                author_stats[author]['clauses_covered'].add(clause['clause_id'])
        
        # Convert sets to counts
        summary = {}
        for author, stats in author_stats.items():
            summary[author] = {
                'documents': stats['documents'],
                'clauses_covered': len(stats['clauses_covered']),
                'is_single_author_risk': stats['documents'] >= 5  # Flag if author owns many docs
            }
        
        return summary
    
    def _extract_scored_evidence(self, doc_text: str, clause: Dict) -> List[Dict]:
        """Extract evidence snippets with relevance scores."""
        evidence = []
        doc_lower = doc_text.lower()
        
        # Modal verb patterns for stronger evidence
        modal_patterns = [
            (r'\bshall\s+\w+', 0.9),
            (r'\bmust\s+\w+', 0.9),
            (r'\brequired\s+to\s+\w+', 0.8),
            (r'\bwill\s+\w+', 0.7),
            (r'\bshould\s+\w+', 0.6)
        ]
        
        # Look for clause keywords in context
        for keyword, weight in clause.get('rake_keywords', [])[:10]:
            keyword_lower = keyword.lower()
            if keyword_lower in doc_lower:
                idx = doc_lower.find(keyword_lower)
                snippet_start = max(0, idx-150)
                snippet_end = min(len(doc_text), idx+150)
                snippet = doc_text[snippet_start:snippet_end].strip()
                
                # Calculate evidence score
                score = 0.5  # Base score for keyword match
                
                # Check for modal verbs in snippet
                import re
                for pattern, modal_score in modal_patterns:
                    if re.search(pattern, snippet.lower()):
                        score = max(score, modal_score)
                        break
                
                # Boost for clause reference
                if clause['id'] in snippet.lower():
                    score = min(score + 0.3, 1.0)
                
                evidence.append({
                    'text': f"...{snippet}...",
                    'score': score,
                    'keyword': keyword,
                    'snippet_from': doc_text.get('doc_id', 'unknown') if isinstance(doc_text, dict) else 'document'
                })
        
        # Sort by score and deduplicate
        evidence.sort(key=lambda x: x['score'], reverse=True)
        
        # Remove overlapping snippets
        unique_evidence = []
        seen_text = set()
        for e in evidence:
            text_key = e['text'][:50]  # First 50 chars as key
            if text_key not in seen_text:
                unique_evidence.append(e)
                seen_text.add(text_key)
        
        return unique_evidence[:5]
    
    def _determine_compliance_status(self, implementing_docs: List[Dict], is_critical: bool) -> str:
        """Determine compliance status with criticality consideration."""
        if not implementing_docs:
            return 'GAP IDENTIFIED'
        
        # For critical clauses, require higher confidence
        threshold = 0.85 if is_critical else 0.75
        
        high_confidence_docs = [d for d in implementing_docs if d['confidence'] > threshold]
        
        if high_confidence_docs:
            return 'COMPLIANT'
        elif any(d['confidence'] > 0.5 for d in implementing_docs):
            return 'PARTIALLY COMPLIANT'
        else:
            return 'NEEDS REVIEW'
    
    def _get_matched_keywords(self, question: str, clause: Dict) -> List[str]:
        """Get keywords that matched between question and clause."""
        question_words = set(question.lower().split())
        clause_keywords = {kw.lower() for kw, _ in clause.get('rake_keywords', [])[:20]}
        
        return list(question_words & clause_keywords)
    
    def _document_addresses_clause(self, doc_text: str, clause: Dict) -> bool:
        """Enhanced check if document addresses a specific AS9100 clause."""
        # Check for explicit clause reference
        clause_id = clause['id']
        if f"as9100" in doc_text and clause_id in doc_text:
            return True
        
        # Check for keyword overlap (increased threshold)
        clause_keywords = [kw.lower() for kw, _ in clause.get('rake_keywords', [])[:15]]
        keyword_matches = sum(1 for kw in clause_keywords if kw in doc_text)
        
        if keyword_matches >= 4:  # Increased from 3
            return True
        
        # Check for requirement language overlap
        for req in clause.get('requirements', [])[:5]:
            key_terms = self._extract_key_terms(req)
            if sum(1 for term in key_terms if term in doc_text) >= 3:  # Increased from 2
                return True
        
        return False
    
    def _calculate_mapping_confidence(self, doc_text: str, clause: Dict) -> float:
        """Enhanced confidence calculation with better scoring."""
        confidence = 0.0
        
        # Explicit reference bonus (reduced to avoid over-reliance)
        if clause['id'] in doc_text and "as9100" in doc_text:
            confidence += 0.4
        
        # Keyword overlap (refined scoring)
        clause_keywords = [kw.lower() for kw, _ in clause.get('rake_keywords', [])[:20]]
        keyword_matches = sum(1 for kw in clause_keywords if kw in doc_text)
        
        # Progressive scoring for keyword matches
        if keyword_matches >= 10:
            confidence += 0.4
        elif keyword_matches >= 5:
            confidence += 0.3
        elif keyword_matches >= 3:
            confidence += 0.2
        else:
            confidence += keyword_matches * 0.05
        
        # Title match (reduced weight)
        if clause['title'].lower() in doc_text:
            confidence += 0.15
        
        # Requirement language match
        req_matches = 0
        for req in clause.get('requirements', [])[:10]:
            if any(term in doc_text for term in self._extract_key_terms(req)):
                req_matches += 1
        
        confidence += min(req_matches * 0.05, 0.2)
        
        return min(confidence, 1.0)
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text."""
        stop_words = {
            'the', 'shall', 'must', 'will', 'be', 'to', 'and', 'or', 'of', 
            'for', 'a', 'an', 'is', 'are', 'by', 'with', 'from', 'as'
        }
        words = text.lower().split()
        return [w for w in words if len(w) > 3 and w not in stop_words][:7]


def create_audit_dashboard_data(
    compliance_system: AS9100ComplianceIntelligence, 
    internal_docs: List[Dict]
) -> Dict:
    """Generate comprehensive data for audit dashboard."""
    
    logger.info("Generating Audit Dashboard Data...")
    
    # Map documents to clauses
    mapping = compliance_system.map_internal_documents(internal_docs)
    compliance_system._last_mapping = mapping  # Store for summary
    
    # Get live snapshot
    snapshot = compliance_system.get_compliance_summary()
    
    dashboard_data = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'compliance_score': snapshot.weighted_score,
            'compliant_percentage': snapshot.compliant,
            'partial_percentage': snapshot.partial,
            'gap_percentage': snapshot.gaps,
            'total_documents': len(internal_docs),
            'covered_clauses': mapping.statistics['covered_clauses'],
            'total_gaps': mapping.statistics['total_gaps'],
            'high_risk_gaps': snapshot.high_risk_gaps,
            'status': 'COMPLIANT' if snapshot.weighted_score > 90 else 'GAPS IDENTIFIED'
        },
        'gaps_by_severity': {
            'HIGH': [],
            'MEDIUM': [],
            'LOW': []
        },
        'clause_coverage': {},
        'author_summary': mapping.statistics.get('author_summary', {}),
        'quick_answers': [],
        'critical_clause_status': {}
    }
    
    # Organize gaps by severity
    for gap in mapping.gaps:
        dashboard_data['gaps_by_severity'][gap['severity']].append(gap)
    
    # Prepare clause coverage for visualization
    for clause_id, docs in mapping.coverage_by_clause.items():
        max_confidence = max(d['confidence'] for d in docs)
        dashboard_data['clause_coverage'][clause_id] = {
            'document_count': len(docs),
            'documents': docs[:3],  # Top 3 docs
            'max_confidence': max_confidence,
            'status': 'COVERED' if max_confidence > 0.8 else 'PARTIAL',
            'is_critical': clause_id in AS9100ComplianceIntelligence.CRITICAL_CLAUSES
        }
    
    # Check critical clause status
    for critical_clause in AS9100ComplianceIntelligence.CRITICAL_CLAUSES:
        if critical_clause in mapping.coverage_by_clause:
            docs = mapping.coverage_by_clause[critical_clause]
            status = 'COMPLIANT' if any(d['confidence'] > 0.85 for d in docs) else 'NEEDS ATTENTION'
        else:
            status = 'NOT COVERED'
        
        dashboard_data['critical_clause_status'][critical_clause] = status
    
    # Add quick answer capabilities
    sample_questions = [
        "What are our supplier control procedures?",
        "Show me risk management requirements",
        "Which documents cover training and competence?",
        "What are the management review requirements?",
        "How do we handle nonconforming outputs?"
    ]
    
    for question in sample_questions:
        answer = compliance_system.answer_compliance_question(question)
        if answer['relevant_clauses']:
            dashboard_data['quick_answers'].append({
                'question': question,
                'top_clause': answer['relevant_clauses'][0],
                'confidence': answer['answers'][0]['relevance_score'] if answer['answers'] else 0
            })
    
    return dashboard_data


# Example usage
if __name__ == "__main__":
    # Initialize compliance intelligence
    compliance_ai = AS9100ComplianceIntelligence()
    
    # Load AS9100 knowledge
    compliance_ai.load_as9100_knowledge()
    
    # Test natural language Q&A with explanation
    questions = [
        "What are the requirements for supplier evaluation?",
        "Show me management review requirements",
        "What does AS9100 say about risk management?"
    ]
    
    for q in questions:
        response = compliance_ai.answer_compliance_question(q, include_explanation=True)
        print(f"\n[INFO] Q: {q}")
        if response['answers']:
            top_answer = response['answers'][0]
            print(f"[INFO] A: {top_answer['clause']}")
            print(f"[INFO]    Relevance: {top_answer['relevance_score']:.2f}")
            print(f"[INFO]    Critical: {top_answer['is_critical']}")
            if top_answer.get('explanation'):
                print(f"[INFO]    Matched Keywords: {top_answer['explanation']['matched_keywords']}")
    
    # Get compliance snapshot
    snapshot = compliance_ai.get_compliance_summary()
    print(f"\n[INFO] Compliance Snapshot:")
    print(f"[INFO]    Weighted Score: {snapshot.weighted_score:.1f}%")
    print(f"[INFO]    High Risk Gaps: {snapshot.high_risk_gaps}")
    
    print("\n" + "="*60)
    print("[SUCCESS] AS9100D Compliance Intelligence System Ready!")
    print("="*60)
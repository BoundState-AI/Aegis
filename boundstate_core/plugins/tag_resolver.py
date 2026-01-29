"""
Tag Resolution System for Athena
Handles tag conflicts and ensures proper tag application
Compliance: SWE-033 (Requirements Traceability)
"""

from __future__ import annotations

__safety_critical__ = False

import logging
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class TagConflict:
    """Represents a tag conflict that needs resolution."""
    primary_tag: str
    conflicting_tag: str
    resolution_rule: str
    priority: float


class TagResolver:
    """Resolves tag conflicts and validates tag application."""
    
    def __init__(self):
        """Initialize with conflict rules and validation patterns."""
        
        # Define explicit tag conflicts
        self.conflicts = [
            TagConflict('Travel_Cost', 'travel_policy', 'exclusive', 1.0),
            TagConflict('Task_Order_Management', 'task_order', 'prefer_primary', 0.9),
            TagConflict('Engineering_Aids', 'engineering', 'prefer_primary', 0.8),
            TagConflict('NASA_Contractor', 'contractor', 'prefer_primary', 0.9),
            TagConflict('Safety_Critical', 'safety', 'prefer_primary', 1.0),
        ]
        
        # Domain keywords for validation
        self.domain_keywords = {
            'Labor_Estimation': ['estimation', 'estimate', 'cost model', 'pricing', 'labor hours'],
            'Engineering_Aids': ['engineering aid', 'technical support', 'ASED', 'engineering tool'],
            'Task_Order_Management': ['task order', 'TO', 'statement of work', 'SOW', 'PWS'],
            'Travel_Cost': ['travel cost', 'per diem', 'lodging', 'airfare', 'travel expense'],
            'Cost_Estimation': ['cost estimate', 'pricing', 'cost model', 'budget', 'financial'],
            'Quality_Planning': ['quality plan', 'QA', 'quality assurance', 'verification', 'validation'],
            'Product_Development': ['product development', 'design', 'prototype', 'development phase'],
            'Verification_Control': ['verification', 'V&V', 'testing', 'validation', 'control'],
            'Criticality_Assessment': ['criticality', 'critical', 'risk assessment', 'hazard'],
            'Safety_Critical': ['safety critical', 'safety', 'hazard', 'risk', 'failure mode'],
        }
        
        # Tag weights from original tagger
        self.tag_weights = {
            'Task_Order_Management': 1.2,
            'Cost_Estimation': 1.1,
            'Quality_Planning': 1.1,
            'Engineering_Aids': 1.0,
            'Product_Development': 1.0,
            'NASA_Contractor': 0.9,
            'Aerospace_Engineering': 0.9,
            'ESSCA_Contract': 1.0,
            'ASED_Process': 1.0,
            'Verification_Control': 1.0,
            'Criticality_Assessment': 1.0,
            'Safety_Critical': 1.1,
            'Finance': 1.0,
            'Procurement': 0.8,
            'ODC': 0.9,
            'Training': 1.0,
            'Travel': 1.0,
            'HR': 0.9,
            'Subcontractor': 0.8,
            'IWA': 0.9,
            'Project_Management': 0.9,
            'Task_Order': 1.0,
            'Contract': 0.8,
            'Materials': 0.9,
        }
    
    def resolve(self, section: Dict[str, Any], discovered_tags: Dict[str, float]) -> List[str]:
        """
        Resolve tag conflicts and validate tags for a section.
        
        Args:
            section: Document section with text and metadata
            discovered_tags: Dictionary of tag -> confidence score
            
        Returns:
            List of resolved tags in priority order
        """
        # Step 1: Apply conflict resolution
        resolved_tags = self._resolve_conflicts(discovered_tags)
        
        # Step 2: Validate tags against domain keywords
        validated_tags = self._validate_domain_keywords(section, resolved_tags)
        
        # Step 3: Apply tag weights
        weighted_tags = self._apply_weights(validated_tags)
        
        # Step 4: Sort by final score and limit
        sorted_tags = sorted(weighted_tags.items(), key=lambda x: x[1], reverse=True)
        
        # Return top tags
        max_tags = 5  # From CONFIG.get('max_tags_per_section', 5)
        return [tag for tag, _ in sorted_tags[:max_tags]]
    
    def _resolve_conflicts(self, tags: Dict[str, float]) -> Dict[str, float]:
        """Resolve explicit tag conflicts."""
        resolved = tags.copy()
        
        for conflict in self.conflicts:
            if conflict.primary_tag in tags and conflict.conflicting_tag in tags:
                if conflict.resolution_rule == 'exclusive':
                    # Only keep the one with higher score
                    if tags[conflict.primary_tag] >= tags[conflict.conflicting_tag]:
                        resolved.pop(conflict.conflicting_tag, None)
                    else:
                        resolved.pop(conflict.primary_tag, None)
                        
                elif conflict.resolution_rule == 'prefer_primary':
                    # Boost primary tag if both present
                    resolved[conflict.primary_tag] = tags[conflict.primary_tag] * conflict.priority
                    resolved[conflict.conflicting_tag] = tags[conflict.conflicting_tag] * 0.5
        
        return resolved
    
    def _validate_domain_keywords(self, section: Dict[str, Any], tags: Dict[str, float]) -> Dict[str, float]:
        """Validate tags against domain keywords in text."""
        validated = {}
        text_lower = section.get('text', '').lower()
        
        for tag, score in tags.items():
            # Check if tag has domain keywords defined
            if tag in self.domain_keywords:
                keywords = self.domain_keywords[tag]
                
                # Check if any keyword is in text
                keyword_found = any(keyword in text_lower for keyword in keywords)
                
                if keyword_found:
                    # Keep original score or boost
                    validated[tag] = score * 1.1
                else:
                    # Penalize but don't remove entirely
                    validated[tag] = score * 0.3
            else:
                # No validation needed, keep as is
                validated[tag] = score
        
        return validated
    
    def _apply_weights(self, tags: Dict[str, float]) -> Dict[str, float]:
        """Apply predefined tag weights."""
        weighted = {}
        
        for tag, score in tags.items():
            weight = self.tag_weights.get(tag, 1.0)
            weighted[tag] = score * weight
        
        return weighted
    
    def get_conflict_info(self, tag1: str, tag2: str) -> Tuple[bool, str]:
        """
        Check if two tags conflict and get resolution info.
        
        Returns:
            (has_conflict, resolution_message)
        """
        for conflict in self.conflicts:
            if (conflict.primary_tag == tag1 and conflict.conflicting_tag == tag2) or \
               (conflict.primary_tag == tag2 and conflict.conflicting_tag == tag1):
                return True, f"Conflict: {conflict.primary_tag} vs {conflict.conflicting_tag} - Rule: {conflict.resolution_rule}"
        
        return False, "No conflict"
    
    def validate_tag_set(self, tags: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate a complete tag set for conflicts.
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for conflicts
        for i, tag1 in enumerate(tags):
            for tag2 in tags[i+1:]:
                has_conflict, message = self.get_conflict_info(tag1, tag2)
                if has_conflict:
                    issues.append(message)
        
        # Check for missing weights
        for tag in tags:
            if tag not in self.tag_weights:
                issues.append(f"Warning: No weight defined for tag '{tag}'")
        
        return len(issues) == 0, issues
    
    def debug_resolution(self, section: Dict[str, Any], discovered_tags: Dict[str, float]) -> Dict[str, Any]:
        """
        Debug tag resolution process.
        
        Returns detailed information about each resolution step.
        """
        debug_info = {
            'original_tags': discovered_tags.copy(),
            'after_conflicts': {},
            'after_validation': {},
            'after_weights': {},
            'final_tags': [],
            'conflicts_found': [],
            'validation_results': {},
            'weights_applied': {}
        }
        
        # Step 1: Conflicts
        resolved = self._resolve_conflicts(discovered_tags)
        debug_info['after_conflicts'] = resolved.copy()
        
        # Find what conflicts were resolved
        for tag in discovered_tags:
            if tag not in resolved or resolved[tag] != discovered_tags[tag]:
                debug_info['conflicts_found'].append(tag)
        
        # Step 2: Validation
        validated = self._validate_domain_keywords(section, resolved)
        debug_info['after_validation'] = validated.copy()
        
        # Record validation results
        text_lower = section.get('text', '').lower()
        for tag in resolved:
            if tag in self.domain_keywords:
                keywords = self.domain_keywords[tag]
                found_keywords = [kw for kw in keywords if kw in text_lower]
                debug_info['validation_results'][tag] = {
                    'keywords_found': found_keywords,
                    'passed': len(found_keywords) > 0
                }
        
        # Step 3: Weights
        weighted = self._apply_weights(validated)
        debug_info['after_weights'] = weighted.copy()
        debug_info['weights_applied'] = {tag: self.tag_weights.get(tag, 1.0) for tag in validated}
        
        # Step 4: Final
        sorted_tags = sorted(weighted.items(), key=lambda x: x[1], reverse=True)
        debug_info['final_tags'] = [tag for tag, _ in sorted_tags[:5]]
        
        return debug_info
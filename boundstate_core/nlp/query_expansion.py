# boundstate/query_expansion.py
"""
Query Expansion for BoundState AI

Handles vocabulary mismatch between user queries and formal document language.
Uses domain-specific expansions and semantic transformations.

Compliance: SWE-013, SWE-033
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)

__all__ = ["QueryExpander", "ExpansionResult", "expand_query"]
__safety_critical__ = False  # NASA SWE-013


@dataclass
class ExpansionResult:
    """Result of query expansion.
    
    Attributes:
        original_query: Original user query
        expanded_queries: List of expanded query variations
        expansion_terms: Key terms added during expansion
        confidence_scores: Confidence for each expansion
        expansion_types: Type of expansion applied (synonym, pattern, etc.)
    """
    original_query: str
    expanded_queries: List[str] = field(default_factory=list)
    expansion_terms: Set[str] = field(default_factory=set)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    expansion_types: Dict[str, str] = field(default_factory=dict)
    
    model_config = {"extra": "forbid", "populate_by_name": True}


class QueryExpander:
    """
    Expands user queries to match formal document vocabulary.
    
    Uses multiple strategies:
    1. Domain-specific synonyms and patterns
    2. Travel/HR policy expansions
    3. Concept decomposition
    4. Formal/informal mappings
    
    Compliance: SWE-033 (Traceability via expansion logging)
    """
    
    def __init__(self):
        """Initialize with domain-specific expansion rules."""
        
        # Travel-specific expansions
        self.travel_expansions = {
            # User terms -> Policy terms
            "stay extra days": ["combine business personal travel", "personal travel", "extend trip"],
            "stay a few extra days": ["combine business personal travel", "personal travel", "extend trip"],
            "extend trip": ["combine business personal travel", "personal arrangements", "additional days"],
            "add vacation": ["combine business personal travel", "personal travel", "leisure travel"],
            "personal days": ["personal travel", "personal arrangements", "non-business days"],
            "extra nights": ["additional lodging", "personal arrangements", "extend stay"],
            "weekend stay": ["personal travel", "non-business days", "personal arrangements"],
            
            # Common travel queries
            "per diem": ["daily allowance", "meal allowance", "incidental expenses", "M&IE"],
            "travel expenses": ["reimbursable expenses", "allowable costs", "travel costs"],
            "book flight": ["travel arrangements", "flight booking", "airfare"],
            "hotel": ["lodging", "accommodation", "overnight stay"],
            "rental car": ["vehicle rental", "ground transportation", "car rental"],
            "mileage": ["mileage reimbursement", "personal vehicle", "mileage rate"],
        }
        
        # HR/Policy expansions
        self.hr_expansions = {
            "time off": ["leave", "PTO", "paid time off", "absence"],
            "vacation": ["annual leave", "vacation leave", "time off"],
            "sick": ["sick leave", "medical leave", "illness"],
            "work from home": ["remote work", "telework", "WFH", "telecommuting"],
            "overtime": ["overtime pay", "overtime hours", "extra hours"],
            "benefits": ["employee benefits", "compensation", "benefits package"],
            "raise": ["salary increase", "compensation adjustment", "pay increase"],
            "promotion": ["advancement", "career progression", "position upgrade"],
        }
        
        # General business expansions
        self.business_expansions = {
            "can i": ["allowed to", "permitted to", "authorized to", "may i"],
            "how to": ["procedure for", "process for", "steps to", "method for"],
            "need to": ["required to", "must", "shall", "obligation to"],
            "what is": ["definition of", "meaning of", "explanation of"],
            "rules for": ["policy on", "guidelines for", "regulations for", "requirements for"],
            "am i eligible": ["eligibility for", "qualify for", "requirements for"],
        }
        
        # Enhanced pattern-based expansions with "a few" fix
        self.pattern_expansions = [
            # Fixed pattern to handle "a few", "some", etc.
            (re.compile(r"\b(stay|extend|add)\s+(a\s+few|some|any)?\s*(extra|additional|more)\s+(days?|nights?)\b", re.I),
             lambda m: ["combine business personal travel", "personal arrangements", "extend travel"]),
            
            (re.compile(r"\b(combine|mix|add)\s+(personal|vacation|leisure)\b", re.I),
             lambda m: ["combine business personal travel", "personal travel", "mixed travel"]),
            
            (re.compile(r"\b(before|after)\s+(business|work)\s+travel\b", re.I),
             lambda m: ["combine business personal travel", "personal travel extension", "travel combination"]),
            
            (re.compile(r"\bweekend\s+(stay|travel|trip)\b", re.I),
             lambda m: ["personal travel", "non-business days", "weekend arrangements"]),
            
            # Question patterns
            (re.compile(r"\bcan\s+i\s+(.+)", re.I),
             lambda m: [f"allowed to {m.group(1)}", f"permitted to {m.group(1)}", f"policy on {m.group(1)}"]),
        ]
        
        # Load custom expansions if available
        self.custom_expansions = self._load_custom_expansions()
        
    def _load_custom_expansions(self) -> Dict[str, List[str]]:
        """Load organization-specific custom expansions.
        
        Returns:
            Custom expansion dictionary
        """
        # TODO: Load from config file or database
        return {
            # Amentum-specific terms
            "pfas": ["per- and polyfluoroalkyl substances", "forever chemicals", "fluorinated compounds"],
            "fod": ["foreign object debris", "foreign object damage"],
            "nda": ["non-disclosure agreement", "confidentiality agreement"],
            "sow": ["statement of work", "scope of work"],
            "ased": ["ASED Travel Office", "travel office", "travel department"],
        }
    
    def expand(self, query: str, max_expansions: int = 5) -> ExpansionResult:
        """
        Expand a user query into multiple variations.
        
        Args:
            query: Original user query
            max_expansions: Maximum number of expansion variations
            
        Returns:
            ExpansionResult with expanded queries and metadata
            
        Compliance: SWE-033 (Full expansion traceability)
        """
        result = ExpansionResult(original_query=query)
        query_lower = query.lower().strip('?.,!')
        
        # Analyze question components for smarter expansion
        components = self._analyze_question_components(query_lower)
        
        # Track unique expansions
        expansions = set()
        expansions.add(query)  # Include original
        
        # Add component-based expansions first (highest priority)
        if components['action'] and components['topic']:
            component_expansions = self._generate_component_expansions(components)
            for exp in component_expansions[:3]:  # Top 3 component expansions
                if exp not in expansions and exp != query:
                    expansions.add(exp)
                    result.expanded_queries.append(exp)
                    result.confidence_scores[exp] = 0.9
                    result.expansion_types[exp] = 'component'
        
        # 1. Direct term expansions
        term_expansions = self._expand_by_terms(query_lower)
        for exp, conf, exp_type in term_expansions:
            if exp not in expansions:
                expansions.add(exp)
                result.expanded_queries.append(exp)
                result.confidence_scores[exp] = conf
                result.expansion_types[exp] = exp_type
                
                # Extract new terms
                new_terms = set(exp.split()) - set(query_lower.split())
                result.expansion_terms.update(new_terms)
        
        # 2. Pattern-based expansions
        pattern_expansions = self._expand_by_patterns(query_lower)
        for exp, conf in pattern_expansions:
            if exp not in expansions:
                expansions.add(exp)
                result.expanded_queries.append(exp)
                result.confidence_scores[exp] = conf
                result.expansion_types[exp] = "pattern"
                
                new_terms = set(exp.split()) - set(query_lower.split())
                result.expansion_terms.update(new_terms)
        
        # 3. Concept decomposition
        concept_expansions = self._expand_by_concepts(query_lower)
        for exp, conf in concept_expansions:
            if exp not in expansions:
                expansions.add(exp)
                result.expanded_queries.append(exp)
                result.confidence_scores[exp] = conf
                result.expansion_types[exp] = "concept"
        
        # 4. Limit expansions
        if len(result.expanded_queries) > max_expansions:
            # Sort by confidence and take top N
            sorted_expansions = sorted(
                result.expanded_queries,
                key=lambda x: result.confidence_scores.get(x, 0),
                reverse=True
            )
            result.expanded_queries = sorted_expansions[:max_expansions]
        
        # Add original query if not already there
        if query not in result.expanded_queries:
            result.expanded_queries.insert(0, query)
            result.confidence_scores[query] = 1.0
            result.expansion_types[query] = "original"
        
        logger.info(f"[QueryExpander] Expanded '{query}' to {len(result.expanded_queries)} variations")
        for exp in result.expanded_queries[:3]:
            logger.debug(f"  - '{exp}' (confidence: {result.confidence_scores.get(exp, 0):.2f})")
        
        return result
    
    def _expand_by_terms(self, query: str) -> List[Tuple[str, float, str]]:
        """Expand query using term dictionaries.
        
        Returns:
            List of (expanded_query, confidence, expansion_type)
        """
        expansions = []
        
        # Check all expansion dictionaries
        all_expansions = [
            (self.travel_expansions, "travel", 0.9),
            (self.hr_expansions, "hr", 0.85),
            (self.business_expansions, "business", 0.8),
            (self.custom_expansions, "custom", 0.85),
        ]
        
        for expansion_dict, exp_type, base_conf in all_expansions:
            for term, replacements in expansion_dict.items():
                if term in query:
                    for replacement in replacements:
                        # Create expanded query
                        expanded = query.replace(term, replacement)
                        if expanded != query:
                            expansions.append((expanded, base_conf, exp_type))
                        
                        # Also try adding as additional context
                        context_expanded = f"{query} {replacement}"
                        expansions.append((context_expanded, base_conf * 0.8, f"{exp_type}_context"))
        
        return expansions
    
    def _expand_by_patterns(self, query: str) -> List[Tuple[str, float]]:
        """Expand query using regex patterns.
        
        Returns:
            List of (expanded_query, confidence)
        """
        expansions = []
        
        for pattern, expansion_func in self.pattern_expansions:
            match = pattern.search(query)
            if match:
                replacement_terms = expansion_func(match)
                
                for term in replacement_terms:
                    # Replace matched portion
                    expanded = pattern.sub(term, query)
                    if expanded != query:
                        expansions.append((expanded, 0.85))
                    
                    # Add as context
                    context_expanded = f"{query} {term}"
                    expansions.append((context_expanded, 0.75))
        
        return expansions
    
    def _expand_by_concepts(self, query: str) -> List[Tuple[str, float]]:
        """Expand query by decomposing concepts.
        
        Returns:
            List of (expanded_query, confidence)
        """
        expansions = []
        
        # Concept mappings
        concepts = {
            "stay extra days": [
                "personal travel after business",
                "extend business trip personal",
                "add personal days business travel"
            ],
            "stay a few extra days": [
                "personal travel after business",
                "extend business trip personal", 
                "combine business personal travel"
            ],
            "combine travel": [
                "business and personal travel",
                "mixed purpose travel",
                "personal extension business trip"
            ],
            "travel policy": [
                "travel guidelines",
                "travel procedures",
                "employee travel rules"
            ],
        }
        
        # Check if query contains any concept
        for concept, variations in concepts.items():
            # Fuzzy match - check if key terms are present
            concept_terms = set(concept.split())
            query_terms = set(query.split())
            
            overlap = len(concept_terms & query_terms) / len(concept_terms)
            if overlap > 0.5:  # At least half the concept terms match
                for variation in variations:
                    expansions.append((variation, 0.7 * overlap))
        
        return expansions
    
    def _analyze_question_components(self, query: str) -> Dict[str, str]:
        """Break down question into semantic components."""
        components = {
            'action': None,
            'topic': None,
            'context': None,
            'modifiers': []
        }
        
        # Action words
        action_patterns = {
            'permission': ['can i', 'may i', 'am i allowed', 'is it okay', 'is it possible'],
            'procedure': ['how do i', 'how to', 'what are the steps', 'process for'],
            'policy': ['what is the policy', 'what are the rules', 'policy on'],
            'definition': ['what is', 'what are', 'define', 'meaning of']
        }
        
        for action_type, patterns in action_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    components['action'] = action_type
                    break
            if components['action']:
                break
        
        # Topic extraction
        topics = {
            'travel': ['travel', 'trip', 'tdy', 'business travel'],
            'personal': ['personal', 'vacation', 'leisure', 'private'],
            'time': ['days', 'hours', 'time', 'duration'],
            'expense': ['expense', 'cost', 'reimburse', 'payment']
        }
        
        for topic_type, keywords in topics.items():
            for keyword in keywords:
                if keyword in query:
                    components['topic'] = topic_type
                    break
        
        # Context modifiers
        if 'extra' in query or 'additional' in query:
            components['modifiers'].append('extra')
        if 'stay' in query or 'extend' in query:
            components['modifiers'].append('extend')
        if 'combine' in query:
            components['modifiers'].append('combine')
        
        # Specific context
        if 'extra days' in query:
            components['context'] = 'extra_days'
        elif 'personal travel' in query:
            components['context'] = 'personal_travel'
        elif 'business travel' in query:
            components['context'] = 'business_travel'
        
        return components
    
    def _generate_component_expansions(self, components: Dict[str, str]) -> List[str]:
        """Generate expansions based on question components."""
        expansions = []
        
        # Permission + Travel queries
        if components['action'] == 'permission' and components['topic'] == 'travel':
            if 'extra' in components.get('modifiers', []):
                expansions.extend([
                    "policy on combining business and personal travel",
                    "rules for extending business travel",
                    "personal travel arrangements policy",
                    "combine business personal travel allowed"
                ])
            else:
                expansions.extend([
                    "travel policy guidelines",
                    "business travel rules",
                    "employee travel authorization"
                ])
        
        # Procedure + Travel queries
        elif components['action'] == 'procedure' and components['topic'] == 'travel':
            expansions.extend([
                "process for travel arrangements",
                "how to book business travel",
                "travel request procedure"
            ])
        
        # Policy queries
        elif components['action'] == 'policy':
            topic = components.get('topic', '')
            expansions.extend([
                f"{topic} policy guidelines",
                f"rules and regulations for {topic}",
                f"company policy on {topic}"
            ])
        
        return expansions


def expand_query(query: str, max_expansions: int = 5) -> ExpansionResult:
    """
    Convenience function to expand a query.
    
    Args:
        query: User query to expand
        max_expansions: Maximum number of expansions
        
    Returns:
        ExpansionResult with expansions
    """
    expander = QueryExpander()
    return expander.expand(query, max_expansions)
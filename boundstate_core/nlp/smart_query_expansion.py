# boundstate/smart_query_expansion.py
from typing import Dict, List, Optional
import json
import os
import logging

from boundstate_core.nlp.query_expansion import QueryExpander, ExpansionResult
from boundstate_core.nlp.query_intelligence import QueryIntelligence

logger = logging.getLogger(__name__)

class SmartQueryExpander(QueryExpander):
    """Enhanced query expansion with domain awareness."""
    
    def __init__(self):
        super().__init__()
        self.query_intelligence = QueryIntelligence()
        self.domain_synonyms = self._load_domain_synonyms()
    
    def _load_domain_synonyms(self) -> Dict[str, List[str]]:
        """Load Amentum-specific synonyms."""
        # Try to load from JSON file if exists
        synonym_file = os.path.join(os.path.dirname(__file__), 'synonyms.json')
        if os.path.exists(synonym_file):
            try:
                with open(synonym_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load synonyms from {synonym_file}: {e}")
        
        # Default synonyms
        return {
            # Travel domain
            "travel": ["trip", "TDY", "business travel", "work travel", "official travel"],
            "personal": ["vacation", "leisure", "non-business", "private", "personal time"],
            "extra days": ["extend", "additional days", "stay longer", "combine", "extension"],
            "stay": ["remain", "extend", "spend time", "lodging"],
            
            # Time off domain
            "PTO": ["paid time off", "vacation", "time off", "leave", "annual leave"],
            "sick": ["illness", "medical", "sick leave", "unwell", "health"],
            
            # Safety domain
            "PPE": ["personal protective equipment", "safety equipment", "protective gear", "safety gear"],
            "incident": ["accident", "injury", "near miss", "safety event", "occurrence"],
            
            # Policy domain
            "policy": ["rule", "regulation", "guideline", "procedure", "directive"],
            "allowed": ["permitted", "authorized", "can", "may", "approved"],
            "required": ["must", "shall", "need to", "have to", "mandatory"],
            
            # Compliance domain
            "compliance": ["conformance", "adherence", "following", "meeting requirements"],
            "standard": ["specification", "requirement", "norm", "criteria"],
            
            # Process domain
            "process": ["procedure", "method", "workflow", "steps"],
            "approval": ["authorization", "permission", "sign-off", "consent"]
        }
    
    def expand(self, query: str, max_expansions: int = 5) -> ExpansionResult:
        """Perform intelligent query expansion."""
        # Analyze query first
        analysis = self.query_intelligence.analyze_query(query)
        
        # Get base expansions from parent class
        base_result = super().expand(query, max_expansions)
        
        # Add domain-specific expansions
        domain_expansions = self._add_domain_expansions(query, analysis)
        
        # Add intent-based expansions
        intent_expansions = self._add_intent_expansions(query, analysis)
        
        # Combine all expansions, removing duplicates
        all_queries = []
        seen = set()
        
        for q in base_result.expanded_queries + domain_expansions + intent_expansions:
            q_lower = q.lower().strip()
            if q_lower not in seen:
                seen.add(q_lower)
                all_queries.append(q)
        
        # Score and rank expansions
        scored_expansions = self._score_expansions(all_queries, analysis)
        
        # Sort by score and take top N
        sorted_queries = sorted(
            all_queries,
            key=lambda q: scored_expansions.get(q, 0),
            reverse=True
        )
        
        # Update the result
        enhanced_result = ExpansionResult(
            original_query=query,
            expanded_queries=sorted_queries[:max_expansions],
            expansion_terms=base_result.expansion_terms,
            confidence_scores=scored_expansions,
            expansion_types=base_result.expansion_types
        )
        
        # Add new expansion terms from domain/intent expansions
        for expansion in enhanced_result.expanded_queries:
            new_terms = set(expansion.lower().split()) - set(query.lower().split())
            enhanced_result.expansion_terms.update(new_terms)
        
        logger.info(f"[SmartQueryExpander] Expanded '{query}' to {len(enhanced_result.expanded_queries)} variations")
        
        return enhanced_result
    
    def _add_domain_expansions(self, query: str, analysis) -> List[str]:
        """Add domain-specific query expansions."""
        expansions = []
        query_lower = query.lower()
        
        # Replace terms with synonyms
        for term, synonyms in self.domain_synonyms.items():
            if term in query_lower:
                for synonym in synonyms:
                    # Skip if synonym is already in query
                    if synonym.lower() in query_lower:
                        continue
                    
                    # Create expansion by replacing term
                    expanded = query_lower.replace(term, synonym)
                    if expanded != query_lower:
                        expansions.append(expanded)
        
        # Add multi-word replacements
        multi_word_replacements = {
            "can i stay": ["am i allowed to stay", "is it permitted to stay", "may i remain"],
            "extra days": ["additional days", "extend my stay", "personal time"],
            "work travel": ["business travel", "official travel", "TDY"],
            "stay a few": ["extend for", "remain for", "add some"]
        }
        
        for phrase, replacements in multi_word_replacements.items():
            if phrase in query_lower:
                for replacement in replacements:
                    expanded = query_lower.replace(phrase, replacement)
                    if expanded != query_lower:
                        expansions.append(expanded)
        
        return expansions
    
    def _add_intent_expansions(self, query: str, analysis) -> List[str]:
        """Add intent-based expansions."""
        expansions = []
        query_lower = query.lower()
        
        if analysis.intent.value == "permission":
            # Add policy-focused expansions
            expansions.extend([
                f"policy on {query_lower}",
                f"rules about {query_lower}",
                f"guidelines for {query_lower}",
                f"is {query_lower} allowed",
                f"authorization for {query_lower}"
            ])
        elif analysis.intent.value == "procedure":
            expansions.extend([
                f"how to {query_lower}",
                f"process for {query_lower}",
                f"steps to {query_lower}",
                f"procedure for {query_lower}"
            ])
        elif analysis.intent.value == "policy":
            expansions.extend([
                f"what are the rules for {query_lower}",
                f"regulations regarding {query_lower}",
                f"compliance requirements for {query_lower}"
            ])
        elif analysis.intent.value == "definition":
            expansions.extend([
                f"what does {query_lower} mean",
                f"definition of {query_lower}",
                f"explain {query_lower}"
            ])
        
        # Add entity-specific expansions
        for entity_type, entities in analysis.entities.items():
            for entity in entities:
                if entity.lower() not in query_lower:
                    expansions.append(f"{query_lower} {entity}")
        
        return expansions
    
    def _score_expansions(self, queries: List[str], analysis) -> Dict[str, float]:
        """Score expansions based on analysis."""
        scores = {}
        
        for query in queries:
            # Base score
            score = 0.5
            
            # Boost if contains entities from analysis
            for entity_list in analysis.entities.values():
                for entity in entity_list:
                    if entity.lower() in query.lower():
                        score += 0.1
            
            # Boost if matches intent patterns
            intent_keywords = {
                "permission": ["allowed", "can", "may", "permitted", "authorized"],
                "procedure": ["how", "process", "steps", "procedure"],
                "policy": ["policy", "rule", "guideline", "regulation"],
                "definition": ["what", "define", "meaning"],
                "compliance": ["requirement", "standard", "compliance"]
            }
            
            if analysis.intent.value in intent_keywords:
                for keyword in intent_keywords[analysis.intent.value]:
                    if keyword in query.lower():
                        score += 0.15
            
            # Boost for domain-specific terms
            domain_terms = ["travel", "policy", "procedure", "compliance", "safety", "ppe"]
            for term in domain_terms:
                if term in query.lower():
                    score += 0.05
            
            # Penalty for being too different from original
            original_terms = set(analysis.intent.name.lower().split())
            query_terms = set(query.lower().split())
            overlap = len(original_terms & query_terms) / max(len(original_terms), 1)
            score *= (0.5 + 0.5 * overlap)
            
            scores[query] = min(1.0, score)
        
        return scores
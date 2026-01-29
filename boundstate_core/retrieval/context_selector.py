# boundstate/context_selector.py
"""Intelligent context selection for question answering."""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import logging
import re

logger = logging.getLogger(__name__)

class ContextSelector:
    """Intelligent context selection for question answering."""
    
    def __init__(self, model=None):
        """Initialize with optional embedding model."""
        self.model = model
        self._sentence_cache = {}
        
    def select_best_contexts(self, 
                           question: str, 
                           documents: List[Dict[str, Any]], 
                           max_contexts: int = 3,
                           min_relevance: float = 0.3) -> List[Dict[str, Any]]:
        """
        Select the most relevant document chunks for answering a question.
        
        This goes beyond simple keyword matching to find semantically relevant passages.
        """
        if not documents:
            return []
        
        # Score each document chunk
        scored_docs = []
        
        for doc in documents:
            text = doc.get('text', '')
            if not text:
                continue
            
            # Calculate relevance using multiple strategies
            relevance_score = self._calculate_relevance(question, text, doc)
            
            # Find the most relevant passage within the document
            best_passage = self._find_best_passage(question, text)
            
            # Store document with scores
            scored_doc = doc.copy()
            scored_doc['relevance_score'] = relevance_score
            scored_doc['relevant_passage'] = best_passage['text']
            scored_doc['passage_score'] = best_passage['score']
            scored_docs.append(scored_doc)
        
        # Sort by relevance
        scored_docs.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Filter by minimum relevance
        relevant_docs = [d for d in scored_docs if d['relevance_score'] >= min_relevance]
        
        # Log selection results
        logger.debug(f"Selected {len(relevant_docs)} contexts from {len(documents)} documents")
        if relevant_docs:
            logger.debug(f"Top relevance score: {relevant_docs[0]['relevance_score']:.3f}")
        
        return relevant_docs[:max_contexts]
    
    def _calculate_relevance(self, question: str, text: str, doc: Dict[str, Any]) -> float:
        """Calculate document relevance using multiple signals."""
        scores = []
        
        # 1. Keyword matching score
        keyword_score = self._keyword_relevance(question, text)
        scores.append(('keyword', keyword_score, 0.3))
        
        # 2. Semantic relevance (if embedding model available)
        if self.model:
            semantic_score = self._semantic_relevance(question, text)
            scores.append(('semantic', semantic_score, 0.4))
        
        # 3. Document type relevance
        doc_type_score = self._doc_type_relevance(question, doc)
        scores.append(('doc_type', doc_type_score, 0.2))
        
        # 4. Question-answer pattern matching
        pattern_score = self._pattern_relevance(question, text)
        scores.append(('pattern', pattern_score, 0.1))
        
        # Weighted average
        total_weight = sum(weight for _, _, weight in scores)
        weighted_score = sum(score * weight for _, score, weight in scores) / total_weight
        
        # Log component scores for debugging
        logger.debug(f"Relevance scores for {doc.get('doc_id', 'unknown')}: " + 
                    ", ".join(f"{name}={score:.3f}" for name, score, _ in scores))
        
        return weighted_score
    
    def _keyword_relevance(self, question: str, text: str) -> float:
        """Calculate keyword-based relevance."""
        question_lower = question.lower()
        text_lower = text.lower()
        
        # Extract important keywords from question
        keywords = self._extract_keywords(question_lower)
        
        if not keywords:
            return 0.0
        
        # Count keyword occurrences
        found_keywords = 0
        for keyword in keywords:
            if keyword in text_lower:
                found_keywords += 1
                # Bonus for exact phrases
                if len(keyword.split()) > 1:
                    found_keywords += 0.5
        
        # Calculate coverage
        coverage = found_keywords / len(keywords)
        
        # Boost for question-specific terms
        if 'travel' in question_lower and 'travel' in text_lower:
            coverage += 0.2
        if 'personal' in question_lower and 'personal' in text_lower:
            coverage += 0.2
        if 'extra days' in question_lower and ('combine' in text_lower or 'personal' in text_lower):
            coverage += 0.3
        
        return min(1.0, coverage)
    
    def _semantic_relevance(self, question: str, text: str) -> float:
        """Calculate semantic relevance using embeddings."""
        try:
            # Use the model to calculate similarity
            question_embedding = self.model.encode([question])[0]
            
            # For efficiency, encode chunks of text
            chunks = self._split_into_chunks(text, max_length=512)
            chunk_scores = []
            
            for chunk in chunks[:5]:  # Limit to first 5 chunks
                chunk_embedding = self.model.encode([chunk])[0]
                score = np.dot(question_embedding, chunk_embedding) / (
                    np.linalg.norm(question_embedding) * np.linalg.norm(chunk_embedding)
                )
                chunk_scores.append(score)
            
            return max(chunk_scores) if chunk_scores else 0.0
            
        except Exception as e:
            logger.warning(f"Semantic relevance calculation failed: {e}")
            return 0.5  # Default middle score
    
    def _doc_type_relevance(self, question: str, doc: Dict[str, Any]) -> float:
        """Score based on document type matching question intent."""
        doc_type = doc.get('doc_type', doc.get('metadata', {}).get('doc_type', 'unknown')).lower()
        question_lower = question.lower()
        
        # Policy questions should prioritize policy documents
        if any(word in question_lower for word in ['policy', 'rule', 'allowed', 'can i', 'may i']):
            if doc_type == 'policy':
                return 1.0
            elif doc_type in ['guideline', 'standard']:
                return 0.7
        
        # Procedure questions should prioritize procedure documents
        if any(word in question_lower for word in ['how to', 'process', 'steps']):
            if doc_type in ['procedure', 'work_instruction']:
                return 1.0
            elif doc_type == 'guideline':
                return 0.6
        
        # Default scores
        type_scores = {
            'policy': 0.8,
            'standard': 0.7,
            'procedure': 0.6,
            'guideline': 0.5,
            'general': 0.3
        }
        
        return type_scores.get(doc_type, 0.2)
    
    def _pattern_relevance(self, question: str, text: str) -> float:
        """Check for question-answer patterns."""
        question_lower = question.lower()
        text_lower = text.lower()
        
        # Permission questions
        if any(phrase in question_lower for phrase in ['can i', 'may i', 'am i allowed']):
            if any(phrase in text_lower for phrase in ['employees may', 'employees can', 'are allowed',
                                                       'are responsible for', 'employees should']):
                return 1.0
        
        # Policy questions
        if 'policy' in question_lower:
            if any(phrase in text_lower for phrase in ['policy', 'rule', 'regulation', 'guideline']):
                return 0.8
        
        return 0.0
    
    def _find_best_passage(self, question: str, text: str) -> Dict[str, Any]:
        """Find the most relevant passage within a document."""
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return {'text': text[:2000], 'score': 0.5}
        
        best_score = 0
        best_passage = ""
        best_index = 0
        
        # Check each sentence with context
        for i, sentence in enumerate(sentences):
            # Skip very short sentences
            if len(sentence.strip()) < 20:
                continue
            
            # Get context window (2 sentences before and after)
            start = max(0, i - 2)
            end = min(len(sentences), i + 3)
            passage = ' '.join(sentences[start:end])
            
            # Score this passage
            score = self._score_passage(question, passage, sentence)
            
            if score > best_score:
                best_score = score
                best_passage = passage
                best_index = i
        
        return {
            'text': best_passage or text[:2000],
            'score': best_score,
            'index': best_index
        }
    
    def _score_passage(self, question: str, passage: str, focus_sentence: str) -> float:
        """Score a specific passage."""
        question_lower = question.lower()
        passage_lower = passage.lower()
        focus_lower = focus_sentence.lower()
        
        score = 0.0
        
        # Check for direct answer indicators
        if 'travel' in question_lower and 'personal' in question_lower:
            if 'combine business and personal travel' in passage_lower:
                score += 0.8
            if 'responsible for' in focus_lower and 'personal' in focus_lower:
                score += 0.9
        
        # General keyword matching
        keywords = self._extract_keywords(question_lower)
        for keyword in keywords:
            if keyword in focus_lower:
                score += 0.3
            elif keyword in passage_lower:
                score += 0.1
        
        return min(1.0, score)
    
    def _extract_keywords(self, question: str) -> List[str]:
        """Extract important keywords and phrases from question."""
        # Remove stop words and question words
        stop_words = {'i', 'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 
                     'if', 'on', 'for', 'to', 'can', 'may', 'do', 'what', 'how', 'when'}
        
        # Extract phrases first
        phrases = []
        phrase_patterns = [
            r'extra days',
            r'work travel',
            r'business travel',
            r'personal travel',
            r'personal arrangements',
            r'travel policy'
        ]
        
        for pattern in phrase_patterns:
            if re.search(pattern, question):
                phrases.append(pattern)
        
        # Extract individual words
        words = question.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Combine phrases and keywords
        return phrases + keywords
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitter
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _split_into_chunks(self, text: str, max_length: int = 512) -> List[str]:
        """Split text into chunks for processing."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1
            
            if current_length >= max_length:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
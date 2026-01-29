# boundstate/system_config.py
"""System-wide configuration for intelligent behavior."""
__safety_critical__ = True  # Critical for query handling

# Relevance thresholds
RELEVANCE_THRESHOLDS = {
    'high': 0.7,      # Very relevant - use this content
    'medium': 0.5,    # Somewhat relevant - include if needed
    'low': 0.3,       # Minimally relevant - use as last resort
    'cutoff': 0.25    # Below this, ignore completely
}

# Question type patterns
QUESTION_PATTERNS = {
    'permission': {
        'patterns': ['can i', 'may i', 'am i allowed', 'is it possible', 'is it okay', 'allowed to'],
        'answer_style': 'yes_no_first',
        'evidence_required': True,
        'boost_doc_types': ['policy', 'guideline'],
        'key_phrases': ['employees may', 'employees can', 'are allowed', 'responsible for']
    },
    'procedure': {
        'patterns': ['how do i', 'how to', 'steps to', 'process for', 'what are the steps'],
        'answer_style': 'step_by_step',
        'evidence_required': True,
        'boost_doc_types': ['procedure', 'work_instruction'],
        'key_phrases': ['step 1', 'first', 'then', 'finally', 'procedure']
    },
    'policy': {
        'patterns': ['what is the policy', 'policy on', 'rules for', 'regulations about'],
        'answer_style': 'cite_policy',
        'evidence_required': True,
        'boost_doc_types': ['policy', 'standard', 'regulation'],
        'key_phrases': ['policy', 'rule', 'regulation', 'requirement']
    },
    'definition': {
        'patterns': ['what is', 'what are', 'define', 'meaning of', 'definition of'],
        'answer_style': 'direct_answer',
        'evidence_required': False,
        'boost_doc_types': ['glossary', 'standard', 'specification'],
        'key_phrases': ['defined as', 'means', 'refers to', 'is a']
    },
    'compliance': {
        'patterns': ['requirements for', 'must i', 'do i need to', 'required to'],
        'answer_style': 'requirements_list',
        'evidence_required': True,
        'boost_doc_types': ['standard', 'regulation', 'compliance'],
        'key_phrases': ['shall', 'must', 'required', 'mandatory']
    }
}

# Document reliability scores
DOC_TYPE_RELIABILITY = {
    'policy': 1.0,           # Official policies are most reliable
    'standard': 0.95,        # Standards are highly reliable
    'specification': 0.9,    # Specs are reliable
    'regulation': 0.9,       # Regulations are reliable
    'procedure': 0.85,       # Procedures are reliable
    'work_instruction': 0.8, # Work instructions are reliable
    'guideline': 0.75,       # Guidelines are somewhat reliable
    'general': 0.5,          # General docs are less reliable
    'unknown': 0.3           # Unknown type docs are least reliable
}

# Answer generation templates
ANSWER_TEMPLATES = {
    'yes_no_first': """Based on {doc_id}: {answer}

Supporting text: "{evidence}"

[Source: {doc_id}, Relevance: {relevance:.2f}]""",
    
    'step_by_step': """According to {doc_id}, here are the steps:

{steps}

[Source: {doc_id}, Relevance: {relevance:.2f}]""",
    
    'cite_policy': """Per {doc_id}:

"{policy_text}"

[Policy Source: {doc_id}, Relevance: {relevance:.2f}]""",
    
    'direct_answer': """{answer}

[Source: {doc_id}, Relevance: {relevance:.2f}]""",
    
    'requirements_list': """Requirements according to {doc_id}:

{requirements}

[Source: {doc_id}, Relevance: {relevance:.2f}]"""
}

# Context quality indicators
QUALITY_INDICATORS = {
    'high_quality': [
        'shall', 'must', 'required', 'employees', 'policy', 
        'procedure', 'approved', 'authorized', 'responsible'
    ],
    'medium_quality': [
        'should', 'recommended', 'guideline', 'typically', 
        'generally', 'normally', 'usually'
    ],
    'low_quality': [
        'may', 'might', 'could', 'possibly', 'sometimes',
        'occasionally', 'varies'
    ]
}

# Special handling for specific topics
TOPIC_HANDLERS = {
    'travel': {
        'key_terms': ['travel', 'trip', 'TDY', 'business travel', 'personal travel'],
        'related_docs': ['POL1901', 'travel policy', 'expense policy'],
        'common_questions': {
            'extra_days': {
                'terms': ['extra days', 'extend', 'personal', 'combine'],
                'target_section': '3.3.3',
                'key_phrase': 'combine business and personal travel'
            },
            'expenses': {
                'terms': ['expense', 'reimburse', 'per diem', 'cost'],
                'target_section': '3.4',
                'key_phrase': 'reimbursable expenses'
            }
        }
    },
    'safety': {
        'key_terms': ['PPE', 'safety', 'hazard', 'protection', 'equipment'],
        'related_docs': ['safety manual', 'PPE requirements'],
        'common_questions': {
            'ppe_required': {
                'terms': ['required PPE', 'need to wear', 'safety equipment'],
                'key_phrase': 'required personal protective equipment'
            }
        }
    },
    'engineering_spec': {
        'key_terms': ['spec', 'ASTM', 'tensile', 'yield', 'material'],
        'related_docs': ['spec manual', 'design guide'],
        'common_questions': {
            'material_spec': {
                'terms': ['spec for', 'properties of', 'requirements for'],
                'key_phrase': 'material specification'
            }
        }
    },
    'tqp': {
        'key_terms': ['tqp', 'technical qualification program'],
        'related_docs': ['training policy', 'qualification guide'],
        'common_questions': {
            'tqp_count': {
                'terms': ['how many', 'count', 'mention tqp'],
                'key_phrase': 'technical qualification program'
            }
        }
    }
}

# Confidence score adjustments
CONFIDENCE_ADJUSTMENTS = {
    'exact_match': 0.3,          # Boost for exact phrase matches
    'section_match': 0.2,        # Boost for matching specific sections
    'doc_type_match': 0.15,      # Boost for matching document types
    'multiple_evidence': 0.1,    # Boost for multiple supporting docs
    'low_relevance_penalty': -0.1, # Reduced penalty for low relevance scores
    'tqp_match': 0.4  # Boost for TQP-specific queries
}
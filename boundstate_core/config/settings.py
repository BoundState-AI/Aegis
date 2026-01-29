#!/usr/bin/env python3
"""Global configuration defaults for the Athena stack.

Compliance: SWE-013, SWE-033
"""

from __future__ import annotations

__safety_critical__ = True  # Critical for system config
__all__ = ['CONFIG']

# RTX 2070 Optimized Configuration
CONFIG = {
    # Chunking - optimized for 420 tokens vs 80 chars (major improvement)
    'use_semantic_chunking': False,
    'chunk_size_tokens': 420,
    'chunk_overlap_tokens': 60,
    'chunk_window': 200,
    'chunk_stride': 100,

    # Embedding model - perfect for RTX 2070
    'model_name': 'nomic-ai/nomic-embed-text-v1.5',
    'batch_size': 128,  # Grok/Fran Opt: Increased from 16 to 128 for GPU
    'device': 'cuda',
    'normalize_embeddings': True,
    'max_seq_length': 8192,

    # Prefixes for Nomic model
    'query_prefix': 'search_query: ',
    'doc_prefix': 'search_document: ',

    # Hybrid search settings (optimized pipeline: 80 -> 80 -> RRF -> 60 -> 12)
    'use_hybrid_search': True,
    'bm25_k1': 1.2,
    'bm25_b': 0.75,
    'rrf_k': 60,
    'topk_dense': 80,
    'topk_bm25': 80,
    'topk_rerank_candidates': 15,
    'topk_rerank': 12,

    # Reranker settings
    'reranker_model': 'mixedbread-ai/mxbai-rerank-base-v1',
    'reranker_device': 'cuda',
    'rerank_batch_size': 8,

    # Index settings
    'index_type': 'IndexFlatIP',
    'use_fp16': True,
    'save_every_sections': 20000,  # Grok/Fran Opt: Save every 20k sections
    'index_autosave_interval': 2000,
    'index_autosave_seconds': 600,
    'tinydb_cache_size': 512,

    # File and database settings
    'tags_file': 'boundstate/tags.json',
    'db_path': 'index/metadata',
    'log_level': 'INFO',
    'allowed_extensions': [
        '.pdf', '.docx', '.doc', '.ppt', '.pptx', '.xls', '.xlsx', '.zip',
        '.txt', '.md', '.mpp', '.png', '.jpg', '.jpeg', '.tiff', '.bmp',
        '.raww'
    ],

    # Ollama settings
    'ollama_model': 'llama3.1:8b-instruct-q4_K_M',  # Confirmed installed; force full GPU offload
    'ollama_fast_model': None,
    'ollama_timeout': 180,
    'ollama_url': 'http://localhost:11434',
    'ollama_keep_alive': '1h',
    'ollama_stream': False,

    'max_context_tokens': 3000,
    'context_char_limit': 1800,
    'doc_context_char_limit': 2000,

    # LLM generation settings (optimized for speed)
    'temperature': 0.0,
    'top_p': 1.0,
    'max_tokens': 500,
    'require_citations': True,
    'answer_max_chars': 2200,

    # LLM execution controls
    'use_two_stage_llm': False,
    'force_big_model_on_table': True,
    'table_mode_terms': ['pto', 'table', 'per diem', 'hours', 'schedule'],
    'fast_model_min_answer_chars': 120,
    'enable_validator_on_fast_model': False,
    'fast_context_char_threshold': 2000,
    'llm_num_ctx': 2048,
    'llm_num_predict': 180,
    'llm_num_thread': 12,  # Increase for Ada GPU parallelism
    'llm_num_gpu': 1,
    'llm_gpu_layers': -1,

    # Prompt template
    'system_prompt': (
        'System: You are Athena. Answer only from the context.\n'
        'If the answer is not present, say: "I cannot find this in the provided documents."\n'
        'Always cite sources as [doc_id section]. Do not reveal chain-of-thought.\n\n'
        'User: {question}\n\nContext:\n<<<\n{context}\n>>>\n\n'
        'Instructions:\n1) Be concise and specific.\n'
        '2) Quote short phrases only when wording matters.\n'
        '3) List all sources you used as [doc_id section].'
    ),

    # Observability settings
    'enable_ranking_trace': True,
    'log_confidence_threshold': 0.7,

    # Speed optimization settings
    'fastpath_top_score': 0.82,

    # System settings
    'use_cag': False,
    'use_ocr_for_figures': True,
    'tqp_threshold': 0.2,
    'policy_doc_types': ['policy', 'hr_policy', 'regulation', 'guideline'],

    # RTX 2070 Memory Management
    'clear_cache_frequency': 10,
    'max_memory_usage_gb': 6,
    'enable_memory_monitoring': True
}

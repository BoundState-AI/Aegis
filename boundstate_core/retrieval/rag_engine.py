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

from __future__ import annotations

import logging
import os
from typing import List, Tuple, Dict, Any, Optional

import chromadb
import requests
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

__safety_critical__ = False


class RetrievedChunk(BaseModel):
    """Retrieved chunk from vector store."""

    document_id: str
    content: str
    score: float
    source: str

    model_config = {"extra": "forbid", "populate_by_name": True}


class RAGAnswer(BaseModel):
    """Structured answer with citations."""
    
    answer: str = Field(description="Generated answer text")
    citations: List[Tuple[str, str]] = Field(
        default_factory=list,
        description="List of (doc_id, snippet) tuples"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if generation failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    model_config = {"extra": "forbid", "populate_by_name": True}

class RAGEngine:
    """BoundState RAG Engine for Semantic Retrieval and Grounded Answering.

    Supports local Ollama models for document Q&A.

    Compliance: SWE-013, SWE-033
    """

    def __init__(self, collection_name: str = "document_chunks"):
        """Initialize the RAG engine.

        Args:
            collection_name: Name of the Chroma collection.
        """
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=OllamaEmbeddingFunction(model_name="nomic-embed-text")
        )

    def index_documents(self, chunks: list[dict[str, str]]) -> None:
        """Index a list of document chunks.

        Each chunk should include 'id', 'document_id', and 'content'.

        Args:
            chunks: List of chunk dictionaries to index.
        """
        ids = [c["id"] for c in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [{"document_id": c["document_id"]} for c in chunks]
        try:
            self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
            logger.info(f"Indexed {len(chunks)} document chunks.")
        except Exception as e:
            logger.error(f"Failed to index documents: {e}")
            raise

    def query(self, question: str, top_k: int = 5) -> list[RetrievedChunk]:
        """Query top matching chunks based on user question.

        Args:
            question: User question to query against.
            top_k: Number of top results to return.

        Returns:
            List of retrieved chunks with scores.

        Raises:
            ValueError: If query fails.
        """
        try:
            results = self.collection.query(query_texts=[question], n_results=top_k)
            retrieved = []
            for i in range(len(results["ids"][0])):
                retrieved.append(RetrievedChunk(
                    document_id=results["metadatas"][0][i]["document_id"],
                    content=results["documents"][0][i],
                    score=results["distances"][0][i],
                    source="chroma_query"
                ))
            return retrieved
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise ValueError(f"Query execution failed: {e}")

    def generate_answer(self, question: str, retrieved_chunks: List[RetrievedChunk]) -> RAGAnswer:
        """Generate a grounded answer using Ollama model.

        Args:
            question: User question to answer.
            retrieved_chunks: Retrieved context chunks.

        Returns:
            RAGAnswer object with answer text and citations.
        """
        # Extract citations with snippets (first 200 chars of each chunk)
        citations = []
        for chunk in retrieved_chunks:
            snippet = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
            citations.append((chunk.document_id, snippet))
        
        # Build context with document IDs
        context = "\n\n".join([f"[{c.document_id}] {c.content}" for c in retrieved_chunks])
        prompt = (
            "You are a compliance analyst AI. Answer the question using only the context below.\n"
            "Include document IDs in your answer when referencing specific information.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )
        
        try:
            # Attempt to connect to Ollama
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30  # 30 second timeout
            )
            response.raise_for_status()
            
            answer_text = response.json()["response"].strip()
            
            return RAGAnswer(
                answer=answer_text,
                citations=citations,
                metadata={
                    "question": question,
                    "num_chunks": len(retrieved_chunks),
                    "model": "llama3.2:latest"
                }
            )
            
        except requests.ConnectionError as e:
            logger.error(f"Failed to connect to Ollama at http://localhost:11434: {e}")
            error_msg = (
                "Unable to connect to Ollama service. Please ensure Ollama is running "
                "with 'ollama serve' and the llama3.2:latest model is available."
            )
            
            # Return structured error response with citations
            return RAGAnswer(
                answer="",
                citations=citations,
                error=error_msg,
                metadata={
                    "question": question,
                    "num_chunks": len(retrieved_chunks),
                    "error_type": "connection_error"
                }
            )
            
        except requests.Timeout as e:
            logger.error(f"Ollama request timed out: {e}")
            error_msg = "Request to Ollama timed out. The model may be loading or unresponsive."
            
            return RAGAnswer(
                answer="",
                citations=citations,
                error=error_msg,
                metadata={
                    "question": question,
                    "num_chunks": len(retrieved_chunks),
                    "error_type": "timeout"
                }
            )
            
        except requests.HTTPError as e:
            logger.error(f"Ollama API returned error: {e}")
            error_msg = f"Ollama API error: {e.response.status_code} - {e.response.text}"
            
            return RAGAnswer(
                answer="",
                citations=citations,
                error=error_msg,
                metadata={
                    "question": question,
                    "num_chunks": len(retrieved_chunks),
                    "error_type": "http_error",
                    "status_code": e.response.status_code
                }
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during answer generation: {e}")
            error_msg = f"Unexpected error: {str(e)}"
            
            return RAGAnswer(
                answer="",
                citations=citations,
                error=error_msg,
                metadata={
                    "question": question,
                    "num_chunks": len(retrieved_chunks),
                    "error_type": "unknown"
                }
            )

    def query_and_answer(self, question: str, top_k: int = 5) -> RAGAnswer:
        """Convenience method to query and generate answer in one call.
        
        Args:
            question: User question to answer
            top_k: Number of chunks to retrieve
            
        Returns:
            RAGAnswer with generated response and citations
        """
        try:
            # Retrieve relevant chunks
            chunks = self.query(question, top_k=top_k)
            
            # Generate answer with citations
            return self.generate_answer(question, chunks)
            
        except Exception as e:
            logger.error(f"Query and answer failed: {e}")
            return RAGAnswer(
                answer="",
                citations=[],
                error=f"Failed to process query: {str(e)}",
                metadata={
                    "question": question,
                    "error_type": "query_error"
                }
            )


__all__ = ["RetrievedChunk", "RAGEngine", "RAGAnswer"]
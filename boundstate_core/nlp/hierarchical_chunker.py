"""
BoundState AI - Hierarchical Chunker
Structure-aware chunking that respects document hierarchy.
Chunks by sections, paragraphs, and tables with intelligent overlaps.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
import re
import logging
from boundstate_core.ingestion.structured_parser import DocumentStructure, Section, Table, Figure

logger = logging.getLogger(__name__)

# Try to import tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None
    TIKTOKEN_AVAILABLE = False

@dataclass
class Chunk:
    """A hierarchical chunk with structure awareness."""
    chunk_id: str
    doc_id: str
    section_path: str
    text: str
    chunk_type: str  # "section", "paragraph", "table", "figure"
    token_count: int
    page_span: Tuple[int, int]
    overlap_with: List[str]  # Other chunk IDs this overlaps with
    metadata: Dict[str, Any]
    
    # Structure-specific fields
    parent_section: Optional[str] = None
    child_chunks: List[str] = None
    table_data: Optional[Table] = None  # If chunk_type == "table"
    figure_data: Optional[Figure] = None  # If chunk_type == "figure"

class HierarchicalChunker:
    """Chunks documents by structure with intelligent overlaps."""
    
    def __init__(self, 
                 max_section_tokens: int = 800,
                 max_paragraph_tokens: int = 400, 
                 overlap_ratio: float = 0.15,
                 min_chunk_tokens: int = 50,
                 token_counter: callable = None):
        """
        Args:
            max_section_tokens: Maximum tokens per section chunk
            max_paragraph_tokens: Maximum tokens per paragraph chunk  
            overlap_ratio: Fraction of overlap between adjacent chunks
            min_chunk_tokens: Minimum tokens to create a chunk
            token_counter: Optional custom token counting function
        """
        self.max_section_tokens = max_section_tokens
        self.max_paragraph_tokens = max_paragraph_tokens
        self.overlap_ratio = overlap_ratio
        self.min_chunk_tokens = min_chunk_tokens
        
        # Set up token counter
        if token_counter:
            self.token_counter = token_counter
        elif TIKTOKEN_AVAILABLE:
            # Use tiktoken for accurate counting
            self.encoder = tiktoken.get_encoding("cl100k_base")  # GPT-4/3.5 encoding
            self.token_counter = self._tiktoken_count
            logger.info("Using tiktoken for accurate token counting")
        else:
            self.token_counter = self._estimate_tokens_heuristic
            logger.warning("tiktoken not available, using heuristic token counting")
    
    def chunk(self, doc_structure: DocumentStructure) -> List[Chunk]:
        """Chunk a document structure into hierarchical chunks."""
        chunks = []
        
        # First pass: Create section-level chunks
        section_chunks = self._chunk_sections(doc_structure)
        chunks.extend(section_chunks)
        
        # Second pass: Create paragraph-level chunks for large sections
        paragraph_chunks = self._chunk_paragraphs(doc_structure, section_chunks)
        chunks.extend(paragraph_chunks)
        
        # Third pass: Create table chunks
        table_chunks = self._chunk_tables(doc_structure)
        chunks.extend(table_chunks)
        
        # Fourth pass: Create figure chunks
        figure_chunks = self._chunk_figures(doc_structure)
        chunks.extend(figure_chunks)
        
        # Fifth pass: Add overlaps between adjacent chunks
        self._add_overlaps(chunks)
        
        logger.info(f"Created {len(chunks)} chunks for {doc_structure.doc_id}")
        return chunks
    
    def _chunk_sections(self, doc_structure: DocumentStructure) -> List[Chunk]:
        """Create section-level chunks."""
        chunks = []
        
        for section in doc_structure.sections:
            token_count = self._estimate_tokens(section.text)
            
            if token_count < self.min_chunk_tokens:
                continue  # Skip very small sections
            
            chunk_id = f"{section.doc_id}_{section.section_path}_section"
            
            # Create section metadata
            metadata = {
                'heading': section.heading,
                'level': section.level,
                'cross_refs': section.cross_refs,
                'tags': section.tags
            }
            
            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=section.doc_id,
                section_path=section.section_path,
                text=section.text,
                chunk_type="section",
                token_count=token_count,
                page_span=section.page_span,
                overlap_with=[],
                metadata=metadata,
                child_chunks=[]
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_paragraphs(self, doc_structure: DocumentStructure, section_chunks: List[Chunk]) -> List[Chunk]:
        """Create paragraph chunks for large sections."""
        chunks = []
        
        for section_chunk in section_chunks:
            # Only chunk paragraphs if section is large
            if section_chunk.token_count <= self.max_section_tokens:
                continue
            
            section = self._find_section_by_path(doc_structure, section_chunk.section_path)
            if not section:
                continue
            
            # Split into paragraphs
            paragraphs = self._split_into_paragraphs(section.text)
            
            para_chunks = []
            for i, paragraph in enumerate(paragraphs):
                token_count = self._estimate_tokens(paragraph)
                
                if token_count < self.min_chunk_tokens:
                    continue
                
                chunk_id = f"{section.doc_id}_{section.section_path}_p{i+1}"
                
                metadata = {
                    'paragraph_index': i,
                    'parent_section': section_chunk.chunk_id,
                    'heading': section.heading
                }
                
                # If paragraph is still too large, split further
                if token_count > self.max_paragraph_tokens:
                    sub_chunks = self._split_large_paragraph(
                        paragraph, chunk_id, section, i, metadata
                    )
                    para_chunks.extend(sub_chunks)
                else:
                    chunk = Chunk(
                        chunk_id=chunk_id,
                        doc_id=section.doc_id,
                        section_path=section.section_path,
                        text=paragraph,
                        chunk_type="paragraph",
                        token_count=token_count,
                        page_span=section.page_span,  # Approximate
                        overlap_with=[],
                        metadata=metadata,
                        parent_section=section_chunk.chunk_id
                    )
                    para_chunks.append(chunk)
            
            # Update parent with child references
            section_chunk.child_chunks = [c.chunk_id for c in para_chunks]
            chunks.extend(para_chunks)
        
        return chunks
    
    def _chunk_tables(self, doc_structure: DocumentStructure) -> List[Chunk]:
        """Create table chunks."""
        chunks = []
        
        for table in doc_structure.tables:
            token_count = self._estimate_tokens(table.extracted_text)
            
            if token_count < self.min_chunk_tokens:
                continue
            
            chunk_id = table.table_id + "_chunk"
            
            # Enhanced table text with structure info
            table_text = self._create_table_text(table)
            
            metadata = {
                'table_id': table.table_id,
                'caption': table.caption,
                'headers': table.headers,
                'row_count': len(table.rows),
                'column_count': len(table.headers) if table.headers else 0
            }
            
            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=table.doc_id,
                section_path=f"table_{table.table_id}",
                text=table_text,
                chunk_type="table",
                token_count=token_count,
                page_span=(table.page, table.page),
                overlap_with=[],
                metadata=metadata,
                table_data=table
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_figures(self, doc_structure: DocumentStructure) -> List[Chunk]:
        """Create figure chunks."""
        chunks = []
        
        for figure in doc_structure.figures:
            if not figure.caption:
                continue  # Skip figures without captions
            
            token_count = self._estimate_tokens(figure.caption + " " + figure.extracted_text)
            
            if token_count < self.min_chunk_tokens:
                continue
            
            chunk_id = figure.figure_id + "_chunk"
            
            # Combine caption and any extracted text
            figure_text = f"Figure: {figure.caption}"
            if figure.extracted_text and figure.extracted_text != figure.caption:
                figure_text += f"\nExtracted text: {figure.extracted_text}"
            
            metadata = {
                'figure_id': figure.figure_id,
                'caption': figure.caption
            }
            
            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=figure.doc_id,
                section_path=f"figure_{figure.figure_id}",
                text=figure_text,
                chunk_type="figure",
                token_count=token_count,
                page_span=(figure.page, figure.page),
                overlap_with=[],
                metadata=metadata,
                figure_data=figure
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split on double newlines or single newlines followed by significant content
        paragraphs = re.split(r'\n\s*\n|\n(?=[A-Z][a-z]|\d+\.|\-\s)', text)
        
        # Clean and filter paragraphs
        clean_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 20:  # Skip very short paragraphs
                clean_paragraphs.append(para)
        
        return clean_paragraphs
    
    def _split_large_paragraph(self, paragraph: str, base_chunk_id: str, 
                              section: Section, para_index: int, 
                              base_metadata: Dict) -> List[Chunk]:
        """Split a large paragraph into smaller chunks with overlap."""
        chunks = []
        
        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        
        current_chunk_text = ""
        current_sentences = []
        chunk_index = 0
        
        for sentence in sentences:
            current_sentences.append(sentence)
            test_text = " ".join(current_sentences)
            
            if self._estimate_tokens(test_text) > self.max_paragraph_tokens:
                # Create chunk from accumulated sentences (minus the current one)
                if len(current_sentences) > 1:
                    chunk_text = " ".join(current_sentences[:-1])
                    
                    chunk_id = f"{base_chunk_id}_s{chunk_index+1}"
                    metadata = base_metadata.copy()
                    metadata['sub_paragraph_index'] = chunk_index
                    
                    chunk = Chunk(
                        chunk_id=chunk_id,
                        doc_id=section.doc_id,
                        section_path=section.section_path,
                        text=chunk_text,
                        chunk_type="paragraph",
                        token_count=self._estimate_tokens(chunk_text),
                        page_span=section.page_span,
                        overlap_with=[],
                        metadata=metadata,
                        parent_section=base_metadata.get('parent_section')
                    )
                    
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Start new chunk with overlap (last few sentences)
                overlap_size = max(1, int(len(current_sentences) * self.overlap_ratio))
                current_sentences = current_sentences[-overlap_size:]
        
        # Handle remaining sentences
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            
            if self._estimate_tokens(chunk_text) >= self.min_chunk_tokens:
                chunk_id = f"{base_chunk_id}_s{chunk_index+1}"
                metadata = base_metadata.copy()
                metadata['sub_paragraph_index'] = chunk_index
                
                chunk = Chunk(
                    chunk_id=chunk_id,
                    doc_id=section.doc_id,
                    section_path=section.section_path,
                    text=chunk_text,
                    chunk_type="paragraph",
                    token_count=self._estimate_tokens(chunk_text),
                    page_span=section.page_span,
                    overlap_with=[],
                    metadata=metadata,
                    parent_section=base_metadata.get('parent_section')
                )
                
                chunks.append(chunk)
        
        return chunks
    
    def _create_table_text(self, table: Table) -> str:
        """Create enhanced searchable text for table."""
        parts = []
        
        # Add caption
        if table.caption:
            parts.append(f"Table Caption: {table.caption}")
        
        # Add structured table data
        parts.append(f"Table ID: {table.table_id}")
        
        if table.headers:
            parts.append(f"Headers: {' | '.join(table.headers)}")
        
        # Add key data rows (limited to avoid noise)
        for i, row in enumerate(table.rows[:8]):  # First 8 rows
            if any(cell.strip() for cell in row):  # Skip empty rows
                row_text = " | ".join(row)
                parts.append(f"Row {i+1}: {row_text}")
        
        if len(table.rows) > 8:
            parts.append(f"... and {len(table.rows) - 8} more rows")
        
        return "\n".join(parts)
    
    def _add_overlaps(self, chunks: List[Chunk]) -> None:
        """Add overlap information between adjacent chunks."""
        # Group chunks by document and section
        by_section = {}
        for chunk in chunks:
            key = f"{chunk.doc_id}_{chunk.section_path}"
            if key not in by_section:
                by_section[key] = []
            by_section[key].append(chunk)
        
        # Add overlaps within each section
        for section_chunks in by_section.values():
            if len(section_chunks) <= 1:
                continue
            
            # Sort by chunk type and ID for consistent ordering
            section_chunks.sort(key=lambda c: (c.chunk_type, c.chunk_id))
            
            for i in range(len(section_chunks) - 1):
                current = section_chunks[i]
                next_chunk = section_chunks[i + 1]
                
                # Only add overlaps for same chunk types
                if current.chunk_type == next_chunk.chunk_type == "paragraph":
                    current.overlap_with.append(next_chunk.chunk_id)
                    next_chunk.overlap_with.append(current.chunk_id)
    
    def _find_section_by_path(self, doc_structure: DocumentStructure, section_path: str) -> Optional[Section]:
        """Find section by path."""
        for section in doc_structure.sections:
            if section.section_path == section_path:
                return section
        return None
    
    def _tiktoken_count(self, text: str) -> int:
        """Accurate token counting using tiktoken."""
        try:
            return len(self.encoder.encode(text))
        except Exception as e:
            logger.warning(f"tiktoken encoding failed: {e}, falling back to heuristic")
            return self._estimate_tokens_heuristic(text)
    
    def _estimate_tokens_heuristic(self, text: str) -> int:
        """Fallback heuristic token estimation (1 token ≈ 4 characters)."""
        return max(1, len(text) // 4)
    
    def _estimate_tokens(self, text: str) -> int:
        """Token estimation using configured counter."""
        return self.token_counter(text)


def main():
    """Test the chunker."""
    import sys
    from boundstate_core.ingestion.structured_parser import StructuredDocumentParser
    
    if len(sys.argv) != 2:
        print("Usage: python hierarchical_chunker.py <pdf_file>")
        sys.exit(1)
    
    # Parse document
    parser = StructuredDocumentParser()
    doc_structure = parser.parse(sys.argv[1])
    
    # Chunk document
    chunker = HierarchicalChunker()
    chunks = chunker.chunk(doc_structure)
    
    print(f"Created {len(chunks)} chunks for {doc_structure.doc_id}")
    
    # Show chunk statistics
    by_type = {}
    for chunk in chunks:
        by_type[chunk.chunk_type] = by_type.get(chunk.chunk_type, 0) + 1
    
    print("Chunks by type:")
    for chunk_type, count in by_type.items():
        print(f"  {chunk_type}: {count}")
    
    # Show first few chunks
    print("\nFirst 3 chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i+1}: {chunk.chunk_id}")
        print(f"  Type: {chunk.chunk_type}")
        print(f"  Section: {chunk.section_path}")
        print(f"  Tokens: {chunk.token_count}")
        print(f"  Pages: {chunk.page_span}")
        print(f"  Text: {chunk.text[:100]}...")


if __name__ == "__main__":
    main()
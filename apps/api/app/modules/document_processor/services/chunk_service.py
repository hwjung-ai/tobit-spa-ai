"""Intelligent document chunking strategy"""

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Metadata for a chunk"""
    position_in_doc: int
    page_number: Optional[int] = None
    chunk_type: str = "text"
    source_hash: Optional[str] = None


class ChunkingStrategy:
    """Multi-strategy chunking based on content type"""

    DEFAULT_CHUNK_SIZE = 512  # tokens
    DEFAULT_OVERLAP = 100  # tokens

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
        document_type: str = "general"
    ) -> List[str]:
        """
        Split text into chunks using smart boundaries

        Strategies:
        1. Sentence-based: Split on sentence boundaries
        2. Paragraph-based: Split on paragraphs (more semantic)
        3. Sliding window: Fixed size with overlap

        Args:
            text: Text to chunk
            chunk_size: Target chunk size in tokens (approx)
            overlap: Overlap size in tokens
            document_type: Type of document (general, code, etc.)

        Returns:
            List of text chunks
        """

        if not text or len(text.strip()) == 0:
            return []

        # Use simple sentence splitting based on punctuation
        sentences = ChunkingStrategy._split_sentences(text)

        if not sentences:
            # Fallback to word-based splitting
            return ChunkingStrategy._split_by_words(text, chunk_size)

        chunks = []
        current_chunk = []
        current_size = 0

        # Approximate token count (rough: words * 1.3)
        for sentence in sentences:
            sentence_tokens = max(1, len(sentence.split()))

            if current_size + sentence_tokens > chunk_size and current_chunk:
                # Finalize current chunk
                chunks.append(" ".join(current_chunk))

                # Add overlap from previous sentences
                if len(current_chunk) > 1 and overlap > 0:
                    overlap_sentences = current_chunk[-1:]
                    current_chunk = overlap_sentences
                    current_size = len(overlap_sentences[0].split())
                else:
                    current_chunk = []
                    current_size = 0

            current_chunk.append(sentence)
            current_size += sentence_tokens

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences"""

        # Simple regex-based sentence splitter
        # Looks for sentence-ending punctuation followed by whitespace
        sentence_pattern = r'(?<=[.!?])\s+'

        sentences = re.split(sentence_pattern, text)

        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def _split_by_words(text: str, chunk_size: int) -> List[str]:
        """Fallback: split by words"""

        words = text.split()
        chunks = []
        current_chunk = []

        for word in words:
            current_chunk.append(word)

            if len(current_chunk) >= chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = []

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    @staticmethod
    def chunk_table(table_data: dict, chunk_size: int = 10) -> List[str]:
        """
        Chunk structured table data

        Args:
            table_data: Dictionary with 'data' and column info
            chunk_size: Number of rows per chunk

        Returns:
            List of text chunks representing table data
        """

        if 'data' not in table_data or not table_data['data']:
            return []

        rows = table_data['data']
        chunks = []

        for i in range(0, len(rows), chunk_size):
            chunk_rows = rows[i:i + chunk_size]

            # Convert rows to readable text
            chunk_text = "Table:\n"
            if 'columns' in table_data:
                chunk_text += ", ".join(table_data['columns']) + "\n"

            for row in chunk_rows:
                if isinstance(row, dict):
                    chunk_text += " | ".join(str(v) for v in row.values()) + "\n"
                elif isinstance(row, (list, tuple)):
                    chunk_text += " | ".join(str(v) for v in row) + "\n"
                else:
                    chunk_text += str(row) + "\n"

            chunks.append(chunk_text)

        return chunks

    @staticmethod
    def compute_source_hash(content: str) -> str:
        """
        Compute hash of content for change detection

        Args:
            content: Content to hash

        Returns:
            SHA256 hash hex string
        """

        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def has_content_changed(old_hash: str, new_content: str) -> bool:
        """
        Check if content has changed

        Args:
            old_hash: Previous content hash
            new_content: New content to check

        Returns:
            True if content differs from hash
        """

        new_hash = ChunkingStrategy.compute_source_hash(new_content)

        return old_hash != new_hash

"""Unit tests for document processor services"""

import pytest
from app.modules.document_processor import (
    DocumentProcessor,
    DocumentProcessingError,
    ChunkingStrategy,
    DocumentExportService,
    ExportFormat,
)


class TestDocumentProcessor:
    """Test document processor format handling"""

    def test_processor_initialization(self):
        """Test processor initialization"""
        processor = DocumentProcessor()
        assert processor.SUPPORTED_FORMATS is not None
        assert "pdf" in processor.SUPPORTED_FORMATS
        assert "docx" in processor.SUPPORTED_FORMATS

    def test_supported_formats(self):
        """Test supported formats"""
        processor = DocumentProcessor()
        supported = processor.SUPPORTED_FORMATS.keys()

        assert "pdf" in supported
        assert "docx" in supported
        assert "xlsx" in supported
        assert "pptx" in supported
        assert "jpg" in supported
        assert "png" in supported

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises error"""
        processor = DocumentProcessor()

        with pytest.raises(DocumentProcessingError):
            processor.process("test.xyz", "xyz")

    def test_unsupported_file_format(self):
        """Test unsupported file format"""
        processor = DocumentProcessor()

        with pytest.raises(DocumentProcessingError):
            processor.process("test.doc", "doc")


class TestChunkingStrategy:
    """Test text chunking strategies"""

    def test_split_sentences(self):
        """Test sentence splitting"""
        text = "This is sentence one. This is sentence two! This is sentence three?"
        sentences = ChunkingStrategy._split_sentences(text)

        assert len(sentences) >= 3
        assert all(isinstance(s, str) for s in sentences)

    def test_chunk_text_basic(self):
        """Test basic text chunking"""
        text = "This is a test document. " * 50  # Create a longer text
        chunks = ChunkingStrategy.chunk_text(text, chunk_size=100)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_chunk_text_empty(self):
        """Test chunking empty text"""
        chunks = ChunkingStrategy.chunk_text("")

        assert len(chunks) == 0

    def test_chunk_table_basic(self):
        """Test table chunking"""
        table_data = {
            "columns": ["Name", "Age", "City"],
            "data": [
                {"Name": "Alice", "Age": 30, "City": "NYC"},
                {"Name": "Bob", "Age": 25, "City": "LA"},
            ]
        }

        chunks = ChunkingStrategy.chunk_table(table_data, chunk_size=1)

        assert len(chunks) == 2
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_compute_source_hash(self):
        """Test content hash computation"""
        content = "test content"
        hash1 = ChunkingStrategy.compute_source_hash(content)
        hash2 = ChunkingStrategy.compute_source_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex is 64 chars

    def test_has_content_changed(self):
        """Test content change detection"""
        old_hash = ChunkingStrategy.compute_source_hash("original")
        
        # Same content
        assert not ChunkingStrategy.has_content_changed(old_hash, "original")
        
        # Different content
        assert ChunkingStrategy.has_content_changed(old_hash, "modified")


class TestDocumentExportService:
    """Test document export functionality"""

    def test_export_to_json(self):
        """Test JSON export"""
        chunks = [
            {"id": "1", "text": "Chunk 1", "page": 1},
            {"id": "2", "text": "Chunk 2", "page": 2},
        ]

        json_str = DocumentExportService.export_chunks_to_json(chunks)

        assert json_str is not None
        assert '"chunks"' in json_str
        assert '"chunk_count": 2' in json_str

    def test_export_to_csv(self):
        """Test CSV export"""
        chunks = [
            {"id": "1", "text": "Chunk 1", "page": 1, "chunk_index": 0},
            {"id": "2", "text": "Chunk 2", "page": 2, "chunk_index": 1},
        ]

        csv_str = DocumentExportService.export_chunks_to_csv(chunks)

        assert csv_str is not None
        assert "chunk_id,chunk_index,page_number" in csv_str
        assert "Chunk 1" in csv_str

    def test_export_to_markdown(self):
        """Test Markdown export"""
        chunks = [
            {"id": "1", "text": "Chunk 1", "page": 1},
            {"id": "2", "text": "Chunk 2", "page": 2},
        ]

        md_str = DocumentExportService.export_chunks_to_markdown(chunks, "Test Doc")

        assert md_str is not None
        assert "# Document: Test Doc" in md_str
        assert "## Chunk 1" in md_str
        assert "## Chunk 2" in md_str

    def test_export_to_text(self):
        """Test plain text export"""
        chunks = [
            {"id": "1", "text": "Chunk 1", "page": 1},
            {"id": "2", "text": "Chunk 2", "page": 2},
        ]

        text_str = DocumentExportService.export_chunks_to_text(chunks, "Test Doc")

        assert text_str is not None
        assert "Document: Test Doc" in text_str
        assert "[Page 1]" in text_str
        assert "Chunk 1" in text_str

    def test_export_chunks_format_selection(self):
        """Test export format selection"""
        chunks = [{"id": "1", "text": "Test"}]

        # JSON
        result = DocumentExportService.export_chunks(chunks, ExportFormat.JSON)
        assert isinstance(result, str)
        assert "chunks" in result

        # CSV
        result = DocumentExportService.export_chunks(chunks, ExportFormat.CSV)
        assert isinstance(result, str)

        # Markdown
        result = DocumentExportService.export_chunks(chunks, ExportFormat.MARKDOWN)
        assert isinstance(result, str)

        # Text
        result = DocumentExportService.export_chunks(chunks, ExportFormat.TEXT)
        assert isinstance(result, str)

    def test_export_unsupported_format(self):
        """Test unsupported export format"""
        chunks = [{"id": "1", "text": "Test"}]

        with pytest.raises(ValueError):
            DocumentExportService.export_chunks(chunks, ExportFormat.PDF)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

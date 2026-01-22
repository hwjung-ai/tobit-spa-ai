"""Document and chat export service for multiple formats"""

import csv
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from io import StringIO
from typing import List, Optional, Union

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats"""

    JSON = "json"
    CSV = "csv"
    MARKDOWN = "md"
    TEXT = "txt"
    PDF = "pdf"  # Would require reportlab/fpdf
    PNG = "png"  # Would require PIL


class DocumentExportService:
    """Export documents and chat conversations in multiple formats"""

    @staticmethod
    def export_chunks_to_json(
        chunks: List[dict],
        document_metadata: Optional[dict] = None
    ) -> str:
        """
        Export document chunks to JSON format

        Args:
            chunks: List of document chunks
            document_metadata: Document metadata

        Returns:
            JSON string
        """

        data = {
            "document": document_metadata or {},
            "chunks": chunks,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "chunk_count": len(chunks)
        }

        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def export_chunks_to_csv(
        chunks: List[dict],
        document_name: Optional[str] = None
    ) -> str:
        """
        Export document chunks to CSV format

        Args:
            chunks: List of document chunks
            document_name: Name of document

        Returns:
            CSV string
        """

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        headers = ["chunk_id", "chunk_index", "page_number", "chunk_type", "text", "created_at"]
        writer.writerow(headers)

        # Write chunks
        for chunk in chunks:
            writer.writerow([
                chunk.get("id", ""),
                chunk.get("chunk_index", ""),
                chunk.get("page_number", ""),
                chunk.get("chunk_type", "text"),
                chunk.get("text", "")[:500],  # Limit text for CSV
                chunk.get("created_at", "")
            ])

        return output.getvalue()

    @staticmethod
    def export_chunks_to_markdown(
        chunks: List[dict],
        document_name: str
    ) -> str:
        """
        Export document chunks to Markdown format

        Args:
            chunks: List of document chunks
            document_name: Name of document

        Returns:
            Markdown string
        """

        lines = [
            f"# Document: {document_name}",
            "",
            f"Exported: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Total chunks: {len(chunks)}",
            ""
        ]

        for i, chunk in enumerate(chunks, 1):
            lines.append(f"## Chunk {i}")
            lines.append("")

            if chunk.get("page_number"):
                lines.append(f"**Page:** {chunk['page_number']}")

            if chunk.get("chunk_type") != "text":
                lines.append(f"**Type:** {chunk.get('chunk_type')}")

            lines.append("")
            lines.append(chunk.get("text", ""))
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def export_chunks_to_text(
        chunks: List[dict],
        document_name: str
    ) -> str:
        """
        Export document chunks to plain text format

        Args:
            chunks: List of document chunks
            document_name: Name of document

        Returns:
            Plain text string
        """

        lines = [
            f"Document: {document_name}",
            f"Exported: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "=" * 80,
            ""
        ]

        for chunk in chunks:
            if chunk.get("page_number"):
                lines.append(f"[Page {chunk['page_number']}]")

            lines.append(chunk.get("text", ""))
            lines.append("")
            lines.append("-" * 80)
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def export_chunks(
        chunks: List[dict],
        format: ExportFormat,
        document_name: str = "export"
    ) -> Union[str, bytes]:
        """
        Export chunks in specified format

        Args:
            chunks: List of document chunks
            format: Export format
            document_name: Document name for headers

        Returns:
            Exported content as string or bytes
        """

        if format == ExportFormat.JSON:
            return DocumentExportService.export_chunks_to_json(
                chunks,
                {"name": document_name}
            )

        elif format == ExportFormat.CSV:
            return DocumentExportService.export_chunks_to_csv(chunks, document_name)

        elif format == ExportFormat.MARKDOWN:
            return DocumentExportService.export_chunks_to_markdown(chunks, document_name)

        elif format == ExportFormat.TEXT:
            return DocumentExportService.export_chunks_to_text(chunks, document_name)

        elif format == ExportFormat.PDF:
            raise ValueError("PDF export requires reportlab library")

        elif format == ExportFormat.PNG:
            raise ValueError("PNG export requires PIL library")

        else:
            raise ValueError(f"Unsupported export format: {format}")


class ChatExportService:
    """Export chat conversations"""

    @staticmethod
    def export_conversation_to_json(
        thread_id: str,
        messages: List[dict],
        metadata: Optional[dict] = None
    ) -> str:
        """Export conversation to JSON"""

        data = {
            "thread_id": thread_id,
            "metadata": metadata or {},
            "messages": messages,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(messages)
        }

        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def export_conversation_to_markdown(
        messages: List[dict],
        title: str = "Conversation"
    ) -> str:
        """Export conversation to Markdown"""

        lines = [
            f"# {title}",
            "",
            f"Exported: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]

        for msg in messages:
            role = msg.get("role", "unknown")
            role_emoji = "👤" if role == "user" else "🤖" if role == "assistant" else "⚙️"

            lines.append(f"## {role_emoji} {role.capitalize()}")
            lines.append("")
            lines.append(msg.get("content", ""))
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def export_conversation(
        messages: List[dict],
        format: ExportFormat,
        title: str = "Conversation"
    ) -> Union[str, bytes]:
        """Export conversation in specified format"""

        if format == ExportFormat.JSON:
            return ChatExportService.export_conversation_to_json(
                thread_id="",
                messages=messages,
                metadata={"title": title}
            )

        elif format == ExportFormat.MARKDOWN:
            return ChatExportService.export_conversation_to_markdown(messages, title)

        else:
            raise ValueError(f"Unsupported export format for chat: {format}")

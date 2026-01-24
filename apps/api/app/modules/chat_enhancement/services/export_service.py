"""Chat export service for multiple formats"""

import csv
import json
import logging
from datetime import datetime
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


class ChatExportService:
    """Export chat conversations"""

    @staticmethod
    def export_to_json(
        thread_id: str, messages: List[dict], metadata: Optional[dict] = None
    ) -> str:
        """Export conversation to JSON"""

        data = {
            "thread_id": thread_id,
            "metadata": metadata or {},
            "messages": messages,
            "exported_at": datetime.utcnow().isoformat(),
            "message_count": len(messages),
        }

        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def export_to_csv(messages: List[dict], title: str = "conversation") -> str:
        """Export conversation to CSV"""

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        headers = ["timestamp", "role", "content", "tokens_in", "tokens_out", "model"]
        writer.writerow(headers)

        # Write messages
        for msg in messages:
            writer.writerow(
                [
                    msg.get("created_at", ""),
                    msg.get("role", ""),
                    msg.get("content", "")[:500],  # Limit content length
                    msg.get("tokens_in", ""),
                    msg.get("tokens_out", ""),
                    msg.get("model", ""),
                ]
            )

        return output.getvalue()

    @staticmethod
    def export_to_markdown(messages: List[dict], title: str = "Conversation") -> str:
        """Export conversation to Markdown"""

        lines = [
            f"# {title}",
            "",
            f"Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Total messages: {len(messages)}",
            "",
        ]

        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            role_emoji = (
                "👤" if role == "user" else "🤖" if role == "assistant" else "⚙️"
            )

            lines.append(f"## {role_emoji} {role.capitalize()}")
            lines.append("")

            content = msg.get("content", "")
            lines.append(content)
            lines.append("")

            if msg.get("tokens_in") or msg.get("tokens_out"):
                tokens = []
                if msg.get("tokens_in"):
                    tokens.append(f"in: {msg['tokens_in']}")
                if msg.get("tokens_out"):
                    tokens.append(f"out: {msg['tokens_out']}")
                lines.append(f"> *Tokens: {', '.join(tokens)}*")
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def export_to_text(messages: List[dict], title: str = "Conversation") -> str:
        """Export conversation to plain text"""

        lines = [
            f"=== {title} ===",
            f"Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total messages: {len(messages)}",
            "",
        ]

        for msg in messages:
            role = msg.get("role", "unknown").upper()
            lines.append(f"[{role}]")
            lines.append(msg.get("content", ""))
            lines.append("")
            lines.append("-" * 80)
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def export_conversation(
        messages: List[dict],
        format: ExportFormat,
        title: str = "Conversation",
        thread_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Union[str, bytes]:
        """Export conversation in specified format"""

        if format == ExportFormat.JSON:
            return ChatExportService.export_to_json(thread_id or "", messages, metadata)

        elif format == ExportFormat.CSV:
            return ChatExportService.export_to_csv(messages, title)

        elif format == ExportFormat.MARKDOWN:
            return ChatExportService.export_to_markdown(messages, title)

        elif format == ExportFormat.TEXT:
            return ChatExportService.export_to_text(messages, title)

        else:
            raise ValueError(f"Unsupported export format: {format}")

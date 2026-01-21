"""Export format definitions"""

from enum import Enum


class ExportFormat(Enum):
    """Supported export formats"""
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    TEXT = "text"
    PDF = "pdf"
    PNG = "png"
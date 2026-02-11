"""
Mock Data Fixtures for OPS Testing

This module contains mock data generators for testing OPS functionality
when real data sources are unavailable.

These fixtures should ONLY be used in test/development environments,
never in production.
"""

from datetime import datetime, timedelta

from app.modules.ops.schemas import (
    AnswerBlock,
    GraphBlock,
    MarkdownBlock,
    TableBlock,
    TimeSeriesBlock,
)


def mock_table() -> TableBlock:
    """Generate mock CI configuration table."""
    return TableBlock(
        type="table",
        title="Sample CI Configuration",
        columns=["Attribute", "Value"],
        rows=[
            ["CI Code", "mes-server-06"],
            ["CI Name", "MES Server 06"],
            ["Type", "System"],
            ["Subtype", "Server"],
            ["Status", "Operational"],
            ["Location", "Data Center A"],
            ["Owner", "Operations Team"],
            ["Created", "2025-01-15"],
            ["Updated", "2026-02-10"],
        ],
    )


def mock_timeseries() -> TimeSeriesBlock:
    """Generate mock time series data for metrics."""
    now = datetime.now()
    data_points = []

    for i in range(24):
        timestamp = (now - timedelta(hours=24 - i)).isoformat()
        cpu_usage = 40 + (i % 5) * 8 + (i // 5) * 3
        memory_usage = 60 + (i % 7) * 3 + (i // 4) * 2
        data_points.append(
            {
                "timestamp": timestamp,
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
            }
        )

    return TimeSeriesBlock(
        type="timeseries",
        title="System Resource Utilization (24h)",
        subtitle="CPU and Memory usage over last 24 hours",
        data=data_points,
    )


def mock_metric_blocks(question: str = "") -> list[AnswerBlock]:
    """Generate mock metric analysis blocks with server name extraction."""
    # Try to extract server number from question
    server_name = "MES Server 06"
    if question:
        import re

        match = re.search(r"(\d{2})", question)
        if match:
            server_num = match.group(1)
            server_name = f"MES Server {server_num}"

    blocks = [
        MarkdownBlock(
            type="markdown",
            title="Performance Summary",
            content=f"**{server_name}** resource utilization metrics for the last 24 hours.",
        ),
        mock_timeseries(),
        TableBlock(
            type="table",
            title="Detailed Metrics",
            columns=["Metric", "Current", "Average", "Peak", "Status"],
            rows=[
                ["CPU Usage", "45%", "42%", "68%", "✅ Normal"],
                ["Memory Usage", "62%", "58%", "74%", "✅ Normal"],
                ["Disk I/O", "12%", "8%", "34%", "✅ Normal"],
                ["Network In/Out", "2.5 Mbps", "1.8 Mbps", "8.3 Mbps", "✅ Normal"],
                ["Process Count", "147", "142", "156", "✅ Normal"],
            ],
        ),
    ]

    return blocks


def mock_graph() -> GraphBlock:
    """Generate mock CI relationship graph."""
    return GraphBlock(
        type="graph",
        title="CI Relationship Graph",
        description="Sample CI infrastructure relationships",
        nodes=[
            {
                "id": "sys-001",
                "label": "MES System",
                "code": "sys-mes-01",
                "type": "System",
                "status": "Operational",
            },
            {
                "id": "srv-001",
                "label": "API Service",
                "code": "srv-api-01",
                "type": "Service",
                "status": "Operational",
            },
            {
                "id": "db-001",
                "label": "Primary Database",
                "code": "db-primary-01",
                "type": "Database",
                "status": "Operational",
            },
        ],
        edges=[
            {"source": "sys-001", "target": "srv-001", "relation": "COMPOSED_OF", "label": "구성"},
            {"source": "srv-001", "target": "db-001", "relation": "USES", "label": "사용"},
        ],
    )


def mock_document_results() -> TableBlock:
    """Generate mock document search results."""
    return TableBlock(
        type="table",
        title="Document Search Results",
        columns=["Document", "Relevance", "Type", "Updated"],
        rows=[
            ["MES System Architecture", "95%", "Design Doc", "2026-01-20"],
            ["API Integration Guide", "87%", "User Manual", "2026-02-01"],
            ["Database Schema Reference", "82%", "Technical Spec", "2026-01-15"],
            ["Troubleshooting Guide", "71%", "FAQ", "2026-02-05"],
            ["Performance Tuning Tips", "68%", "Best Practice", "2025-12-30"],
        ],
    )

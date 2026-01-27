"""
ConnectionFactory Pattern - Dynamic source connection management.

This module provides a factory pattern for creating connections to different
data sources (PostgreSQL, Neo4j, REST API, etc.) based on source asset configuration.
"""

from __future__ import annotations

from .factory import ConnectionFactory, create_connection

__all__ = ["ConnectionFactory", "create_connection"]

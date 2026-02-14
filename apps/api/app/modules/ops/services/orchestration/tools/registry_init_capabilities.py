"""
Initialize default tool capabilities in the registry (P1-2).
This module is imported to ensure all tool capabilities are registered.
"""

from app.modules.ops.services.orchestration.tools.capability_registry import (
    initialize_default_capabilities,
)

# Initialize default capabilities on module import
initialize_default_capabilities()

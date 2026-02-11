"""
Runtime Tool Discovery System

This module provides functionality to dynamically discover and load tools
at runtime without requiring application restart. It supports:
1. Periodic scanning of the Asset Registry for new tools
2. Webhook-based updates for immediate tool registration
3. Health monitoring and validation of loaded tools
4. Automatic refresh of tool configurations

This enables a truly dynamic orchestration system where new tools can be
added and used immediately without deployment.
"""

import asyncio
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.db import get_session_context
from core.logging import get_logger

from app.modules.asset_registry.crud import list_assets
from app.modules.asset_registry.models import TbAssetRegistry

from .base import ToolRegistry, get_tool_registry

logger = get_logger(__name__)


class DiscoveryMode(Enum):
    """Tool discovery modes."""
    PERIODIC = "periodic"  # Scan on a schedule
    WEBHOOK = "webhook"     # Update on webhook triggers
    HYBRID = "hybrid"       # Both periodic and webhook


class ToolChangeType(Enum):
    """Types of tool changes detected."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


@dataclass
class ToolChange:
    """Represents a change in tool registry."""
    change_type: ToolChangeType
    tool_name: str
    tool_info: Optional[Dict[str, Any]] = None
    detected_at: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"{self.change_type.value.title()} tool: {self.tool_name}"


class RuntimeToolDiscovery:
    """
    Runtime tool discovery system that monitors Asset Registry for changes
    and dynamically updates the tool registry.

    Features:
    - Periodic scanning with configurable intervals
    - Webhook endpoint for immediate updates
    - Change detection and notification
    - Health validation of tools
    - Automatic reload capabilities
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        scan_interval: int = 60,  # seconds
        webhook_enabled: bool = True,
        auto_refresh: bool = True,
        health_check_interval: int = 300  # 5 minutes
    ):
        """
        Initialize the discovery system.

        Args:
            registry: ToolRegistry instance (creates new if None)
            scan_interval: How often to scan for changes (seconds)
            webhook_enabled: Enable webhook-based updates
            auto_refresh: Automatically refresh tools when changes detected
            health_check_interval: How often to check tool health (seconds)
        """
        self.registry = registry or get_tool_registry()
        self.scan_interval = scan_interval
        self.webhook_enabled = webhook_enabled
        self.auto_refresh = auto_refresh
        self.health_check_interval = health_check_interval

        # State tracking
        self.last_scan_time: Optional[datetime] = None
        self.last_health_check: Optional[datetime] = None
        self._running = False
        self._scan_thread: Optional[threading.Thread] = None
        self._health_thread: Optional[threading.Thread] = None

        # Event callbacks
        self._change_callbacks: List[Callable[[ToolChange], None]] = []
        self._error_callbacks: List[Callable[[Exception], None]] = []

        # Cache for tool state comparison
        self._cached_tools: Dict[str, Dict[str, Any]] = {}

        # Webhook secret for security
        self.webhook_secret: Optional[str] = None

        logger.info(f"RuntimeToolDiscovery initialized with scan_interval={scan_interval}s")

    def add_change_callback(self, callback: Callable[[ToolChange], None]) -> None:
        """Add a callback to be invoked when tools change."""
        self._change_callbacks.append(callback)

    def add_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """Add a callback to be invoked when errors occur."""
        self._error_callbacks.append(callback)

    def set_webhook_secret(self, secret: str) -> None:
        """Set webhook secret for authentication."""
        self.webhook_secret = secret
        logger.info("Webhook secret configured")

    async def start_discovery(self) -> None:
        """Start the discovery system."""
        if self._running:
            logger.warning("Discovery already running")
            return

        self._running = True
        logger.info("Starting runtime tool discovery...")

        # Start scanning thread
        self._scan_thread = threading.Thread(
            target=self._scan_loop,
            daemon=True,
            name="ToolDiscoveryScanner"
        )
        self._scan_thread.start()

        # Start health check thread
        if self.health_check_interval > 0:
            self._health_thread = threading.Thread(
                target=self._health_check_loop,
                daemon=True,
                name="ToolDiscoveryHealthCheck"
            )
            self._health_thread.start()

        # Initial scan
        await self.scan_for_changes()

        logger.info("Runtime tool discovery started")

    async def stop_discovery(self) -> None:
        """Stop the discovery system."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping runtime tool discovery...")

        # Wait for threads to finish
        if self._scan_thread and self._scan_thread.is_alive():
            self._scan_thread.join(timeout=5)

        if self._health_thread and self._health_thread.is_alive():
            self._health_thread.join(timeout=5)

        logger.info("Runtime tool discovery stopped")

    async def scan_for_changes(self, force: bool = False) -> List[ToolChange]:
        """
        Scan for tool changes in the Asset Registry.

        Args:
            force: Force scan even if interval hasn't elapsed

        Returns:
            List of detected changes
        """
        if not force and self.last_scan_time:
            elapsed = (datetime.now() - self.last_scan_time).total_seconds()
            if elapsed < self.scan_interval:
                return []

        changes = []

        try:
            # Get current tools from Asset Registry
            with get_session_context() as session:
                db_tools = list_assets(
                    session=session,
                    asset_type="tool",
                    status="published",
                )

            # Current tools (as dict for comparison)
            current_tools = {
                tool.name: {
                    "tool_type": tool.tool_type,
                    "version": tool.version,
                    "updated_at": tool.updated_at,
                    "tool_config": tool.tool_config,
                    "tags": tool.tags
                }
                for tool in db_tools
            }

            # Detect changes
            changes = self._detect_tool_changes(current_tools)

            # Update cache
            self._cached_tools = current_tools
            self.last_scan_time = datetime.now()

            # Auto-refresh if enabled
            if self.auto_refresh and changes:
                await self._refresh_tools(changes)

            logger.info(f"Scan complete: {len(changes)} changes detected")

        except Exception as e:
            logger.error(f"Error during tool scan: {str(e)}")
            for callback in self._error_callbacks:
                try:
                    callback(e)
                except Exception as cb_e:
                    logger.error(f"Error in error callback: {str(cb_e)}")

        return changes

    def _detect_tool_changes(self, current_tools: Dict[str, Dict[str, Any]]) -> List[ToolChange]:
        """Detect differences between current and cached tools."""
        changes = []

        # Check for new or updated tools
        for tool_name, tool_info in current_tools.items():
            if tool_name not in self._cached_tools:
                # New tool
                changes.append(ToolChange(
                    change_type=ToolChangeType.CREATED,
                    tool_name=tool_name,
                    tool_info=tool_info
                ))
            elif self._cached_tools[tool_name] != tool_info:
                # Updated tool
                changes.append(ToolChange(
                    change_type=ToolChangeType.UPDATED,
                    tool_name=tool_name,
                    tool_info=tool_info
                ))

        # Check for deleted tools
        for tool_name in self._cached_tools:
            if tool_name not in current_tools:
                changes.append(ToolChange(
                    change_type=ToolChangeType.DELETED,
                    tool_name=tool_name
                ))

        return changes

    async def _refresh_tools(self, changes: List[ToolChange]) -> None:
        """Refresh tools based on detected changes."""
        for change in changes:
            try:
                if change.change_type in [ToolChangeType.CREATED, ToolChangeType.UPDATED]:
                    # Load and register the tool
                    await self._load_tool_from_registry(change.tool_name)
                    logger.info(f"Refreshed tool: {change.tool_name}")

                elif change.change_type == ToolChangeType.DELETED:
                    # Remove from registry
                    if change.tool_name in self.registry._instances:
                        del self.registry._instances[change.tool_name]
                        logger.info(f"Removed tool: {change.tool_name}")

                # Notify callbacks
                for callback in self._change_callbacks:
                    try:
                        callback(change)
                    except Exception as e:
                        logger.error(f"Error in change callback: {str(e)}")

            except Exception as e:
                logger.error(f"Error refreshing tool {change.tool_name}: {str(e)}")
                for callback in self._error_callbacks:
                    try:
                        callback(e)
                    except Exception as cb_e:
                        logger.error(f"Error in error callback: {str(cb_e)}")

    async def _load_tool_from_registry(self, tool_name: str) -> None:
        """Load a tool from Asset Registry and register it."""
        with get_session_context() as session:
            tool = session.query(TbAssetRegistry).filter(
                TbAssetRegistry.asset_type == "tool",
                TbAssetRegistry.status == "published",
                TbAssetRegistry.name == tool_name,
            ).first()

            if not tool:
                raise ValueError(f"Tool {tool_name} not found")

            # Create DynamicTool instance
            from .dynamic_tool import DynamicTool

            dynamic_tool = DynamicTool(
                {
                    "asset_id": str(tool.asset_id),
                    "name": tool.name,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "tool_config": tool.tool_config or {},
                    "tool_input_schema": tool.tool_input_schema,
                    "tool_output_schema": tool.tool_output_schema,
                }
            )

            # Register with global registry
            self.registry.register_dynamic(dynamic_tool)

    async def check_tool_health(self, tool_names: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Health check for registered tools.

        Args:
            tool_names: Specific tools to check (None for all)

        Returns:
            Dictionary mapping tool names to health status
        """
        health_status = {}

        tools_to_check = tool_names or list(self.registry._instances.keys())

        for tool_name in tools_to_check:
            try:
                tool = self.registry.get_tool(tool_name)

                # Perform basic validation
                if hasattr(tool, 'tool_type') and hasattr(tool, 'tool_name'):
                    health_status[tool_name] = True
                else:
                    health_status[tool_name] = False

            except Exception as e:
                logger.error(f"Health check failed for {tool_name}: {str(e)}")
                health_status[tool_name] = False

        self.last_health_check = datetime.now()
        return health_status

    def _scan_loop(self) -> None:
        """Background thread for periodic scanning."""
        while self._running:
            try:
                # Run scan in async context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.scan_for_changes())
                finally:
                    loop.close()

                # Wait for next scan
                for _ in range(self.scan_interval):
                    if not self._running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in scan loop: {str(e)}")
                time.sleep(5)  # Wait before retry

    def _health_check_loop(self) -> None:
        """Background thread for periodic health checks."""
        while self._running:
            try:
                # Run health check in async context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    health_status = loop.run_until_complete(self.check_tool_health())
                    unhealthy_tools = [name for name, healthy in health_status.items() if not healthy]
                    if unhealthy_tools:
                        logger.warning(f"Unhealthy tools detected: {unhealthy_tools}")
                finally:
                    loop.close()

                # Wait for next health check
                for _ in range(self.health_check_interval):
                    if not self._running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in health check loop: {str(e)}")
                time.sleep(30)  # Wait before retry

    # Webhook endpoint methods
    async def handle_webhook(self, payload: Dict[str, Any], signature: Optional[str] = None) -> bool:
        """
        Handle webhook payload for immediate tool updates.

        Args:
            payload: Webhook payload containing tool changes
            signature: Optional signature for verification

        Returns:
            True if processed successfully
        """
        if not self.webhook_enabled:
            logger.warning("Webhook disabled but received webhook call")
            return False

        # Verify signature if provided
        if self.webhook_secret and signature:
            if not self._verify_webhook_signature(payload, signature):
                logger.error("Invalid webhook signature")
                return False

        try:
            # Parse payload and trigger scan
            changes = await self.scan_for_changes(force=True)
            logger.info(f"Webhook processed: {len(changes)} changes")
            return True

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return False

    def _verify_webhook_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """Verify webhook signature using HMAC."""
        import hashlib
        import hmac
        import json

        payload_str = json.dumps(payload, sort_keys=True)
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def get_discovery_status(self) -> Dict[str, Any]:
        """Get current discovery system status."""
        return {
            "running": self._running,
            "last_scan_time": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "scan_interval": self.scan_interval,
            "health_check_interval": self.health_check_interval,
            "registered_tools": len(self.registry._instances),
            "cached_tools": len(self._cached_tools),
            "webhook_enabled": self.webhook_enabled,
            "auto_refresh": self.auto_refresh
        }


# Global discovery instance
_discovery_instance: Optional[RuntimeToolDiscovery] = None


def get_runtime_discovery(
    scan_interval: int = 60,
    webhook_enabled: bool = True,
    auto_refresh: bool = True
) -> RuntimeToolDiscovery:
    """Get or create the global runtime discovery instance."""
    global _discovery_instance

    if _discovery_instance is None:
        _discovery_instance = RuntimeToolDiscovery(
            scan_interval=scan_interval,
            webhook_enabled=webhook_enabled,
            auto_refresh=auto_refresh
        )

    return _discovery_instance


async def start_runtime_discovery(
    scan_interval: int = 60,
    webhook_enabled: bool = True,
    auto_refresh: bool = True
) -> RuntimeToolDiscovery:
    """Start the global runtime discovery system."""
    discovery = get_runtime_discovery(scan_interval, webhook_enabled, auto_refresh)
    await discovery.start_discovery()
    return discovery

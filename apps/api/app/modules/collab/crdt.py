"""CRDT (Conflict-free Replicated Data Type) implementation for real-time collaboration.

This module provides CRDT-based data structures for collaborative editing,
specifically designed for screen schema editing with automatic conflict resolution.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class CRDTOperation:
    """Represents a single CRDT operation."""
    
    op_id: str  # Unique operation ID
    op_type: str  # Type of operation (insert, delete, update, move)
    timestamp: datetime
    user_id: str  # User who performed the operation
    component_id: str  # Target component ID
    parent_id: Optional[str] = None  # Parent component for hierarchy
    path: Optional[List[str]] = None  # JSON path for nested updates
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    index: Optional[int] = None  # For insert/move operations
    position: Optional[str] = None  # 'before' or 'after'
    reference_id: Optional[str] = None  # Reference component for before/after


@dataclass
class CRDTComponent:
    """Represents a component with CRDT metadata."""
    
    component_id: str
    data: Dict[str, Any]
    version: int = 0
    deleted: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    updated_by: str = ""
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "component_id": self.component_id,
            "data": self.data,
            "version": self.version,
            "deleted": self.deleted,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "parent_id": self.parent_id,
            "children": self.children
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CRDTComponent":
        """Create from dictionary."""
        return cls(
            component_id=data["component_id"],
            data=data["data"],
            version=data.get("version", 0),
            deleted=data.get("deleted", False),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
            created_by=data.get("created_by", ""),
            updated_by=data.get("updated_by", ""),
            parent_id=data.get("parent_id"),
            children=data.get("children", [])
        )


class CRDTDocument:
    """
    CRDT-based document for collaborative editing.
    
    Implements a Last-Writer-Wins (LWW) register for components and
    an operation log for conflict-free synchronization.
    """
    
    def __init__(self, document_id: str):
        """Initialize CRDT document."""
        self.document_id = document_id
        self.components: Dict[str, CRDTComponent] = {}  # component_id -> component
        self.operation_log: List[CRDTOperation] = []
        self.version = 0
        
    def apply_operation(self, operation: CRDTOperation) -> bool:
        """
        Apply an operation to the document.
        
        Args:
            operation: CRDT operation to apply
            
        Returns:
            True if operation was applied successfully
        """
        try:
            if operation.op_type == "insert":
                self._apply_insert(operation)
            elif operation.op_type == "delete":
                self._apply_delete(operation)
            elif operation.op_type == "update":
                self._apply_update(operation)
            elif operation.op_type == "move":
                self._apply_move(operation)
            else:
                logger.warning(f"Unknown operation type: {operation.op_type}")
                return False
            
            self.operation_log.append(operation)
            self.version += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply operation: {e}", exc_info=True)
            return False
    
    def _apply_insert(self, op: CRDTOperation):
        """Apply insert operation."""
        if op.component_id in self.components:
            # Component already exists, treat as update
            self._apply_update(op)
            return
        
        # Create new component
        component = CRDTComponent(
            component_id=op.component_id,
            data=op.new_value or {},
            created_by=op.user_id,
            updated_by=op.user_id,
            parent_id=op.parent_id
        )
        
        # Handle position in hierarchy
        if op.parent_id:
            parent = self.components.get(op.parent_id)
            if parent:
                if op.position == "before" and op.reference_id:
                    # Insert before reference
                    if op.reference_id in parent.children:
                        idx = parent.children.index(op.reference_id)
                        parent.children.insert(idx, op.component_id)
                    else:
                        parent.children.append(op.component_id)
                elif op.position == "after" and op.reference_id:
                    # Insert after reference
                    if op.reference_id in parent.children:
                        idx = parent.children.index(op.reference_id)
                        parent.children.insert(idx + 1, op.component_id)
                    else:
                        parent.children.append(op.component_id)
                else:
                    # Append to end
                    parent.children.append(op.component_id)
        
        self.components[op.component_id] = component
    
    def _apply_delete(self, op: CRDTOperation):
        """Apply delete operation."""
        component = self.components.get(op.component_id)
        if not component or component.deleted:
            return
        
        # Mark as deleted (soft delete for CRDT)
        component.deleted = True
        component.updated_by = op.user_id
        component.updated_at = op.timestamp
        component.version += 1
        
        # Remove from parent's children
        if component.parent_id:
            parent = self.components.get(component.parent_id)
            if parent and op.component_id in parent.children:
                parent.children.remove(op.component_id)
    
    def _apply_update(self, op: CRDTOperation):
        """Apply update operation (LWW register)."""
        component = self.components.get(op.component_id)
        if not component:
            # Component doesn't exist, treat as insert
            self._apply_insert(op)
            return
        
        if component.deleted:
            # Component was deleted, recreate it
            component.deleted = False
            component.created_by = op.user_id
            component.created_at = op.timestamp
        
        # Update data based on path
        if op.path:
            # Deep update using path
            current = component.data
            for key in op.path[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[op.path[-1]] = op.new_value
        else:
            # Full update
            component.data = op.new_value or {}
        
        component.updated_by = op.user_id
        component.updated_at = op.timestamp
        component.version += 1
    
    def _apply_move(self, op: CRDTOperation):
        """Apply move operation (reorder component)."""
        component = self.components.get(op.component_id)
        if not component or component.deleted:
            return
        
        if not op.parent_id:
            return
        
        # Remove from current parent
        if component.parent_id:
            old_parent = self.components.get(component.parent_id)
            if old_parent and op.component_id in old_parent.children:
                old_parent.children.remove(op.component_id)
        
        # Add to new parent
        new_parent = self.components.get(op.parent_id)
        if not new_parent:
            return
        
        component.parent_id = op.parent_id
        component.updated_by = op.user_id
        component.updated_at = op.timestamp
        component.version += 1
        
        # Insert at new position
        if op.position == "before" and op.reference_id:
            if op.reference_id in new_parent.children:
                idx = new_parent.children.index(op.reference_id)
                new_parent.children.insert(idx, op.component_id)
            else:
                new_parent.children.append(op.component_id)
        elif op.position == "after" and op.reference_id:
            if op.reference_id in new_parent.children:
                idx = new_parent.children.index(op.reference_id)
                new_parent.children.insert(idx + 1, op.component_id)
            else:
                new_parent.children.append(op.component_id)
        else:
            new_parent.children.append(op.component_id)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current document state."""
        return {
            "document_id": self.document_id,
            "version": self.version,
            "components": [
                comp.to_dict() 
                for comp in self.components.values() 
                if not comp.deleted
            ]
        }
    
    def get_operations_since(self, since_version: int) -> List[CRDTOperation]:
        """Get operations since a specific version."""
        return self.operation_log[since_version:]


class CRDTManager:
    """Manages CRDT documents and synchronization."""
    
    def __init__(self, redis_client=None):
        """Initialize CRDT manager."""
        from core.redis import get_redis_client
        self.redis_client = redis_client or get_redis_client()
        self.documents: Dict[str, CRDTDocument] = {}
        
    def get_document(self, document_id: str) -> CRDTDocument:
        """Get or create document."""
        if document_id not in self.documents:
            # Try to load from Redis
            saved_state = self.redis_client.get(f"crdt:doc:{document_id}")
            if saved_state:
                try:
                    doc = self._deserialize_document(json.loads(saved_state))
                    self.documents[document_id] = doc
                    return doc
                except Exception as e:
                    logger.error(f"Failed to deserialize document: {e}")
            
            # Create new document
            self.documents[document_id] = CRDTDocument(document_id)
        
        return self.documents[document_id]
    
    def apply_operation(self, document_id: str, operation: CRDTOperation) -> Dict[str, Any]:
        """
        Apply operation and return updated state.
        
        Args:
            document_id: Document ID
            operation: Operation to apply
            
        Returns:
            Updated document state
        """
        doc = self.get_document(document_id)
        success = doc.apply_operation(operation)
        
        if success:
            # Persist to Redis
            self._persist_document(doc)
        
        return {
            "success": success,
            "document_id": document_id,
            "version": doc.version,
            "state": doc.get_state()
        }
    
    def sync_operations(self, document_id: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sync operations from client to server.
        
        Args:
            document_id: Document ID
            operations: List of operations to sync
            
        Returns:
            Server response with state and missing operations
        """
        doc = self.get_document(document_id)
        
        # Apply operations in order
        for op_data in operations:
            op = CRDTOperation(
                op_id=op_data["op_id"],
                op_type=op_data["op_type"],
                timestamp=datetime.fromisoformat(op_data["timestamp"]),
                user_id=op_data["user_id"],
                component_id=op_data["component_id"],
                parent_id=op_data.get("parent_id"),
                path=op_data.get("path"),
                old_value=op_data.get("old_value"),
                new_value=op_data.get("new_value"),
                index=op_data.get("index"),
                position=op_data.get("position"),
                reference_id=op_data.get("reference_id")
            )
            doc.apply_operation(op)
        
        # Persist
        self._persist_document(doc)
        
        # Return operations since client version
        client_version = operations[-1].get("document_version", 0) if operations else 0
        missing_ops = doc.get_operations_since(client_version)
        
        return {
            "document_id": document_id,
            "version": doc.version,
            "state": doc.get_state(),
            "missing_operations": [
                {
                    "op_id": op.op_id,
                    "op_type": op.op_type,
                    "timestamp": op.timestamp.isoformat(),
                    "user_id": op.user_id,
                    "component_id": op.component_id,
                    "parent_id": op.parent_id,
                    "path": op.path,
                    "old_value": op.old_value,
                    "new_value": op.new_value,
                    "index": op.index,
                    "position": op.position,
                    "reference_id": op.reference_id
                }
                for op in missing_ops
            ]
        }
    
    def _persist_document(self, doc: CRDTDocument):
        """Persist document to Redis."""
        try:
            state = {
                "document_id": doc.document_id,
                "version": doc.version,
                "components": [comp.to_dict() for comp in doc.components.values()],
                "operation_log": [
                    {
                        "op_id": op.op_id,
                        "op_type": op.op_type,
                        "timestamp": op.timestamp.isoformat(),
                        "user_id": op.user_id,
                        "component_id": op.component_id,
                        "parent_id": op.parent_id,
                        "path": op.path,
                        "old_value": op.old_value,
                        "new_value": op.new_value,
                        "index": op.index,
                        "position": op.position,
                        "reference_id": op.reference_id
                    }
                    for op in doc.operation_log
                ]
            }
            
            # Persist with TTL
            self.redis_client.set(
                f"crdt:doc:{doc.document_id}",
                json.dumps(state),
                ex=86400  # 24 hours
            )
            
        except Exception as e:
            logger.error(f"Failed to persist document: {e}")
    
    def _deserialize_document(self, data: Dict[str, Any]) -> CRDTDocument:
        """Deserialize document from saved state."""
        doc = CRDTDocument(data["document_id"])
        doc.version = data.get("version", 0)
        
        # Deserialize components
        for comp_data in data.get("components", []):
            comp = CRDTComponent.from_dict(comp_data)
            doc.components[comp.component_id] = comp
        
        # Deserialize operation log
        for op_data in data.get("operation_log", []):
            op = CRDTOperation(
                op_id=op_data["op_id"],
                op_type=op_data["op_type"],
                timestamp=datetime.fromisoformat(op_data["timestamp"]),
                user_id=op_data["user_id"],
                component_id=op_data["component_id"],
                parent_id=op_data.get("parent_id"),
                path=op_data.get("path"),
                old_value=op_data.get("old_value"),
                new_value=op_data.get("new_value"),
                index=op_data.get("index"),
                position=op_data.get("position"),
                reference_id=op_data.get("reference_id")
            )
            doc.operation_log.append(op)
        
        return doc


# Global CRDT manager instance
crdt_manager = CRDTManager()


class CollaborationSession:
    """Manages a user's collaboration session."""
    
    def __init__(self, session_id: str, user_id: str, document_id: str):
        """Initialize collaboration session."""
        self.session_id = session_id
        self.user_id = user_id
        self.document_id = document_id
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
        
    def is_stale(self, timeout_seconds: int = 300) -> bool:
        """Check if session is stale (no activity for timeout)."""
        delta = datetime.utcnow() - self.last_activity
        return delta.total_seconds() > timeout_seconds
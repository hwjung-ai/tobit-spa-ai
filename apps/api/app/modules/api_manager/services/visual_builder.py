"""Visual Builder service for API Manager.

Provides templates and schema for visual API builder (React Flow based).
"""

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class NodeTemplate(BaseModel):
    """Template for a visual builder node."""
    
    node_id: str
    node_type: str  # sql, http, python, workflow, condition, loop
    name: str
    description: str
    category: str  # database, api, logic, flow
    icon: str  # Icon identifier
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    config_schema: Dict[str, Any]
    default_config: Optional[Dict[str, Any]] = None


class ConnectionTemplate(BaseModel):
    """Template for node connections."""
    
    source_node_type: str
    target_node_type: str
    allowed: bool
    condition: Optional[str] = None


class VisualBuilderTemplate:
    """Manages visual builder templates and schemas."""
    
    # Node templates
    NODE_TEMPLATES: Dict[str, NodeTemplate] = {
        "sql": NodeTemplate(
            node_id="sql-node",
            node_type="sql",
            name="SQL Query",
            description="Execute SQL query on database",
            category="database",
            icon="database",
            inputs=[
                {"id": "query", "type": "string", "required": True, "label": "SQL Query"},
                {"id": "params", "type": "object", "required": False, "label": "Parameters"}
            ],
            outputs=[
                {"id": "result", "type": "array", "label": "Query Result"},
                {"id": "rows_affected", "type": "number", "label": "Rows Affected"}
            ],
            config_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "title": "SQL Query",
                        "description": "SQL SELECT/WITH query only",
                        "default": ""
                    },
                    "params": {
                        "type": "object",
                        "title": "Parameters",
                        "description": "Query parameters",
                        "default": {}
                    }
                },
                "required": ["query"]
            }
        ),
        "http": NodeTemplate(
            node_id="http-node",
            node_type="http",
            name="HTTP Request",
            description="Make HTTP request to external API",
            category="api",
            icon="globe",
            inputs=[
                {"id": "url", "type": "string", "required": True, "label": "URL"},
                {"id": "method", "type": "string", "required": True, "label": "Method"},
                {"id": "headers", "type": "object", "required": False, "label": "Headers"},
                {"id": "body", "type": "object", "required": False, "label": "Body"}
            ],
            outputs=[
                {"id": "response", "type": "object", "label": "Response"},
                {"id": "status", "type": "number", "label": "Status Code"}
            ],
            config_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "title": "URL",
                        "default": ""
                    },
                    "method": {
                        "type": "string",
                        "title": "Method",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                        "default": "GET"
                    },
                    "headers": {
                        "type": "object",
                        "title": "Headers",
                        "default": {}
                    },
                    "body": {
                        "type": "object",
                        "title": "Body",
                        "default": {}
                    },
                    "timeout": {
                        "type": "number",
                        "title": "Timeout (seconds)",
                        "default": 30
                    }
                },
                "required": ["url", "method"]
            }
        ),
        "python": NodeTemplate(
            node_id="python-node",
            node_type="python",
            name="Python Script",
            description="Execute Python script",
            category="logic",
            icon="code",
            inputs=[
                {"id": "script", "type": "string", "required": True, "label": "Python Script"},
                {"id": "params", "type": "object", "required": False, "label": "Parameters"}
            ],
            outputs=[
                {"id": "result", "type": "object", "label": "Execution Result"}
            ],
            config_schema={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "title": "Python Script",
                        "description": "Python code with main(params, input_payload) function",
                        "default": "def main(params, input_payload):\n    return {'result': 'hello'}"
                    },
                    "params": {
                        "type": "object",
                        "title": "Parameters",
                        "default": {}
                    }
                },
                "required": ["script"]
            }
        ),
        "condition": NodeTemplate(
            node_id="condition-node",
            node_type="condition",
            name="Condition",
            description="Conditional branching",
            category="logic",
            icon="git-branch",
            inputs=[
                {"id": "condition", "type": "string", "required": True, "label": "Condition"},
                {"id": "input", "type": "any", "required": False, "label": "Input Data"}
            ],
            outputs=[
                {"id": "true", "type": "any", "label": "True Path"},
                {"id": "false", "type": "any", "label": "False Path"}
            ],
            config_schema={
                "type": "object",
                "properties": {
                    "condition": {
                        "type": "string",
                        "title": "Condition Expression",
                        "description": "Python-like expression (e.g., input.value > 10)",
                        "default": ""
                    }
                },
                "required": ["condition"]
            }
        ),
        "loop": NodeTemplate(
            node_id="loop-node",
            node_type="loop",
            name="Loop",
            description="Iterate over array",
            category="flow",
            icon="repeat",
            inputs=[
                {"id": "items", "type": "array", "required": True, "label": "Items"},
                {"id": "body", "type": "any", "required": True, "label": "Loop Body"}
            ],
            outputs=[
                {"id": "results", "type": "array", "label": "Iteration Results"}
            ],
            config_schema={
                "type": "object",
                "properties": {
                    "item_variable": {
                        "type": "string",
                        "title": "Item Variable Name",
                        "default": "item"
                    },
                    "index_variable": {
                        "type": "string",
                        "title": "Index Variable Name",
                        "default": "index"
                    }
                }
            }
        )
    }
    
    # Connection rules
    CONNECTION_RULES: List[ConnectionTemplate] = [
        ConnectionTemplate(source_node_type="sql", target_node_type="http", allowed=True),
        ConnectionTemplate(source_node_type="sql", target_node_type="python", allowed=True),
        ConnectionTemplate(source_node_type="sql", target_node_type="condition", allowed=True),
        ConnectionTemplate(source_node_type="http", target_node_type="python", allowed=True),
        ConnectionTemplate(source_node_type="http", target_node_type="condition", allowed=True),
        ConnectionTemplate(source_node_type="python", target_node_type="sql", allowed=True),
        ConnectionTemplate(source_node_type="python", target_node_type="http", allowed=True),
        ConnectionTemplate(source_node_type="python", target_node_type="python", allowed=True),
        ConnectionTemplate(source_node_type="python", target_node_type="condition", allowed=True),
        ConnectionTemplate(source_node_type="condition", target_node_type="sql", allowed=True, condition="true"),
        ConnectionTemplate(source_node_type="condition", target_node_type="http", allowed=True, condition="true"),
        ConnectionTemplate(source_node_type="condition", target_node_type="python", allowed=True, condition="true"),
        ConnectionTemplate(source_node_type="condition", target_node_type="sql", allowed=True, condition="false"),
        ConnectionTemplate(source_node_type="condition", target_node_type="http", allowed=True, condition="false"),
        ConnectionTemplate(source_node_type="condition", target_node_type="python", allowed=True, condition="false"),
        ConnectionTemplate(source_node_type="loop", target_node_type="sql", allowed=True),
        ConnectionTemplate(source_node_type="loop", target_node_type="http", allowed=True),
        ConnectionTemplate(source_node_type="loop", target_node_type="python", allowed=True),
    ]
    
    @staticmethod
    def get_node_templates() -> Dict[str, Dict[str, Any]]:
        """Get all node templates for visual builder."""
        return {
            node_id: node.model_dump()
            for node_id, node in VisualBuilderTemplate.NODE_TEMPLATES.items()
        }
    
    @staticmethod
    def get_node_template(node_type: str) -> Optional[Dict[str, Any]]:
        """Get specific node template."""
        node = VisualBuilderTemplate.NODE_TEMPLATES.get(node_type)
        return node.model_dump() if node else None
    
    @staticmethod
    def validate_connection(
        source_node_type: str,
        target_node_type: str,
        condition: Optional[str] = None
    ) -> bool:
        """
        Validate if connection between nodes is allowed.
        
        Args:
            source_node_type: Source node type
            target_node_type: Target node type
            condition: Optional condition (for condition nodes)
            
        Returns:
            True if connection is allowed
        """
        for rule in VisualBuilderTemplate.CONNECTION_RULES:
            if (rule.source_node_type == source_node_type and 
                rule.target_node_type == target_node_type and
                rule.allowed):
                
                # Check condition if specified
                if rule.condition:
                    if condition != rule.condition:
                        continue
                
                return True
        
        return False
    
    @staticmethod
    def validate_workflow(workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate workflow definition.
        
        Args:
            workflow_data: Workflow definition with nodes and edges
            
        Returns:
            Validation result with errors if any
        """
        errors = []
        warnings = []
        
        nodes = workflow_data.get("nodes", [])
        edges = workflow_data.get("edges", [])
        
        # Check if workflow has nodes
        if not nodes:
            errors.append("Workflow must have at least one node")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Check for start nodes
        start_nodes = [n for n in nodes if n.get("data", {}).get("isStart", False)]
        if not start_nodes:
            warnings.append("No start node defined")
        
        # Validate each node
        node_ids = set()
        for node in nodes:
            node_id = node.get("id")
            node_type = node.get("data", {}).get("type")
            
            if not node_id:
                errors.append(f"Node missing id: {node}")
                continue
            
            if node_id in node_ids:
                errors.append(f"Duplicate node id: {node_id}")
                continue
            
            node_ids.add(node_id)
            
            # Validate node type exists
            template = VisualBuilderTemplate.NODE_TEMPLATES.get(node_type)
            if not template:
                errors.append(f"Unknown node type: {node_type}")
                continue
            
            # Validate required fields
            config = node.get("data", {}).get("config", {})
            for field_name, field_config in template.config_schema.get("properties", {}).items():
                if field_config.get("required", False) and field_name not in config:
                    errors.append(f"Node {node_id} missing required field: {field_name}")
        
        # Validate each edge
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            source_handle = edge.get("sourceHandle")
            
            if not source or not target:
                errors.append(f"Edge missing source or target: {edge}")
                continue
            
            source_node = next((n for n in nodes if n.get("id") == source), None)
            if not source_node:
                errors.append(f"Edge source node not found: {source}")
                continue
            
            source_node_type = source_node.get("data", {}).get("type")
            target_node = next((n for n in nodes if n.get("id") == target), None)
            if not target_node:
                errors.append(f"Edge target node not found: {target}")
                continue
            
            target_node_type = target_node.get("data", {}).get("type")
            
            # Validate connection
            condition = None
            if source_node_type == "condition" and source_handle:
                condition = source_handle
            
            if not VisualBuilderTemplate.validate_connection(
                source_node_type, 
                target_node_type, 
                condition
            ):
                errors.append(
                    f"Invalid connection: {source_node_type} -> {target_node_type}"
                )
        
        is_valid = len(errors) == 0
        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings
        }
    
    @staticmethod
    def export_workflow_to_json(workflow_data: Dict[str, Any]) -> str:
        """
        Export workflow to JSON format.
        
        Args:
            workflow_data: Workflow definition
            
        Returns:
            JSON string
        """
        return json.dumps(workflow_data, indent=2, default=str)
    
    @staticmethod
    def import_workflow_from_json(json_str: str) -> Dict[str, Any]:
        """
        Import workflow from JSON.
        
        Args:
            json_str: JSON string
            
        Returns:
            Workflow definition
        """
        try:
            workflow_data = json.loads(json_str)
            
            # Validate
            validation = VisualBuilderTemplate.validate_workflow(workflow_data)
            if not validation["valid"]:
                raise ValueError(f"Invalid workflow: {validation['errors']}")
            
            return workflow_data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to import workflow: {e}", exc_info=True)
            raise


# Global template manager
visual_builder = VisualBuilderTemplate()
"""
Topology Ingestor for Simulation System

**IMPORTANT**: This is NOT a topology collection agent!

This module provides CLIENT CODE to connect to EXISTING infrastructure:

- Kubernetes API (user's existing K8s cluster)
- AWS CloudFormation (user's existing AWS stacks)
- Azure Resource Graph (optional)

Users must already have these infrastructure systems running.
This code only fetches topology data from them via their APIs.

For actual infrastructure discovery, see:
- Kubernetes native resources
- AWS CloudFormation stacks
- Infrastructure as Code tools
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Node(BaseModel):
    """Topology node representation"""
    id: str
    name: str
    type: str  # "service", "deployment", "pod", "database", "queue", etc.
    properties: dict[str, Any] = Field(default_factory=dict)
    labels: dict[str, str] = Field(default_factory=dict)


class Edge(BaseModel):
    """Topology edge (relationship) representation"""
    source: str
    target: str
    type: str  # "depends_on", "calls", "hosts", "reads_from", etc.
    properties: dict[str, Any] = Field(default_factory=dict)


class TopologyGraph(BaseModel):
    """Complete topology graph"""
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TopologyIngestorConfig(BaseModel):
    """Configuration for topology collection"""
    k8s_api_server: Optional[str] = None
    k8s_token: Optional[str] = None
    k8s_ca_cert: Optional[str] = None
    aws_region: Optional[str] = None
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    azure_subscription_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    neo4j_uri: Optional[str] = None
    neo4j_user: Optional[str] = None
    neo4j_password: Optional[str] = None


class BaseTopologyIngestor(ABC):
    """Abstract base class for topology collectors"""

    @abstractmethod
    async def collect(self, **kwargs) -> TopologyGraph:
        """Collect topology graph"""
        pass


class KubernetesIngestor(BaseTopologyIngestor):
    """Collect topology from Kubernetes API"""

    def __init__(
        self,
        api_server: str,
        token: Optional[str] = None,
        ca_cert: Optional[str] = None,
    ):
        self.api_server = api_server.rstrip("/")
        self.token = token
        self.ca_cert = ca_cert
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    async def collect(
        self,
        namespace: str = "default",
        include_pods: bool = True,
        include_services: bool = True,
        include_deployments: bool = True,
    ) -> TopologyGraph:
        """
        Collect Kubernetes resources and build topology graph.

        Args:
            namespace: Kubernetes namespace
            include_pods: Include pods in graph
            include_services: Include services in graph
            include_deployments: Include deployments in graph

        Returns:
            TopologyGraph with nodes and edges
        """
        nodes = []
        edges = []

        async with httpx.AsyncClient(verify=self.ca_cert or False, timeout=30.0) as client:
            # Collect Services
            if include_services:
                services = await self._get_services(client, namespace)
                nodes.extend(services["nodes"])
                edges.extend(services["edges"])

            # Collect Deployments
            if include_deployments:
                deployments = await self._get_deployments(client, namespace)
                nodes.extend(deployments["nodes"])
                edges.extend(deployments["edges"])

            # Collect Pods
            if include_pods:
                pods = await self._get_pods(client, namespace)
                nodes.extend(pods["nodes"])
                edges.extend(pods["edges"])

        return TopologyGraph(
            nodes=nodes,
            edges=edges,
            metadata={
                "source": "kubernetes",
                "namespace": namespace,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
        )

    async def _get_services(
        self, client: httpx.AsyncClient, namespace: str
    ) -> dict[str, Any]:
        """Get services from Kubernetes"""
        url = f"{self.api_server}/api/v1/namespaces/{namespace}/services"
        response = await client.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()

        nodes = []
        edges = []

        for svc in data.get("items", []):
            metadata = svc.get("metadata", {})
            spec = svc.get("spec", {})

            node_id = metadata.get("name", "")
            nodes.append(Node(
                id=f"service:{node_id}",
                name=node_id,
                type="service",
                properties={
                    "cluster_ip": spec.get("clusterIP", ""),
                    "external_ip": ", ".join(spec.get("externalIPs", [])),
                    "ports": [p.get("port") for p in spec.get("ports", [])],
                    "selector": spec.get("selector", {}),
                },
                labels=metadata.get("labels", {}),
            ))

            # Service -> Pod edges (via selector)
            selector = spec.get("selector", {})
            if selector:
                selector_str = ",".join(f"{k}={v}" for k, v in selector.items())
                edges.append(Edge(
                    source=f"service:{node_id}",
                    target=f"pod_selector:{selector_str}",
                    type="selects",
                    properties={"selector": selector},
                ))

        return {"nodes": nodes, "edges": edges}

    async def _get_deployments(
        self, client: httpx.AsyncClient, namespace: str
    ) -> dict[str, Any]:
        """Get deployments from Kubernetes"""
        url = f"{self.api_server}/apis/apps/v1/namespaces/{namespace}/deployments"
        response = await client.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()

        nodes = []
        edges = []

        for deploy in data.get("items", []):
            metadata = deploy.get("metadata", {})
            spec = deploy.get("spec", {})
            status = deploy.get("status", {})

            node_id = metadata.get("name", "")
            replicas = spec.get("replicas", 0)

            nodes.append(Node(
                id=f"deployment:{node_id}",
                name=node_id,
                type="deployment",
                properties={
                    "replicas": replicas,
                    "available_replicas": status.get("availableReplicas", 0),
                    "ready_replicas": status.get("readyReplicas", 0),
                    "image": spec.get("template", {}).get("spec", {}).get("containers", [{}])[0].get("image", ""),
                },
                labels=metadata.get("labels", {}),
            ))

            # Deployment -> Pod relationship
            labels = metadata.get("labels", {})
            if labels:
                edges.append(Edge(
                    source=f"deployment:{node_id}",
                    target=f"pod_selector:{','.join(f'{k}={v}' for k, v in labels.items())}",
                    type="creates",
                    properties={"replicas": replicas},
                ))

        return {"nodes": nodes, "edges": edges}

    async def _get_pods(
        self, client: httpx.AsyncClient, namespace: str
    ) -> dict[str, Any]:
        """Get pods from Kubernetes"""
        url = f"{self.api_server}/api/v1/namespaces/{namespace}/pods"
        response = await client.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()

        nodes = []
        edges = []

        for pod in data.get("items", []):
            metadata = pod.get("metadata", {})
            spec = pod.get("spec", {})
            status = pod.get("status", {})

            node_id = metadata.get("name", "")
            phase = status.get("phase", "Unknown")

            nodes.append(Node(
                id=f"pod:{node_id}",
                name=node_id,
                type="pod",
                properties={
                    "phase": phase,
                    "node_name": spec.get("nodeName", ""),
                    "pod_ip": status.get("podIP", ""),
                    "host_ip": status.get("hostIP", ""),
                    "restart_count": sum(c.get("restartCount", 0) for c in status.get("containerStatuses", [])),
                },
                labels=metadata.get("labels", {}),
            ))

            # Pod -> Node relationship
            node_name = spec.get("nodeName", "")
            if node_name:
                edges.append(Edge(
                    source=f"pod:{node_id}",
                    target=f"node:{node_name}",
                    type="runs_on",
                    properties={},
                ))

        return {"nodes": nodes, "edges": edges}


class CloudFormationIngestor(BaseTopologyIngestor):
    """Collect topology from AWS CloudFormation"""

    def __init__(
        self,
        region: str,
        access_key: str,
        secret_key: str,
    ):
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self._client = None

    @property
    def client(self):
        """Lazy initialization of CloudFormation client"""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "cloudformation",
                    region_name=self.region,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                )
            except ImportError:
                logger.warning("boto3 not installed. CloudFormation collection unavailable.")
        return self._client

    async def collect(
        self,
        stack_name: str,
        include_resources: bool = True,
    ) -> TopologyGraph:
        """
        Collect CloudFormation stack resources.

        Args:
            stack_name: CloudFormation stack name
            include_resources: Include resources in graph

        Returns:
            TopologyGraph with nodes and edges
        """
        if not self.client:
            logger.warning("CloudFormation client not available")
            return TopologyGraph()

        try:
            # Get stack resources
            response = self.client.describe_stack_resources(StackName=stack_name)
            resources = response.get("StackResources", [])

            nodes = []
            edges = []

            for resource in resources:
                resource_id = resource.get("PhysicalResourceId", "")
                resource_type = resource.get("ResourceType", "")
                logical_id = resource.get("LogicalResourceId", "")

                nodes.append(Node(
                    id=f"resource:{resource_id}",
                    name=logical_id,
                    type=resource_type.split("::")[-1] if "::" in resource_type else resource_type,
                    properties={
                        "physical_id": resource_id,
                        "logical_id": logical_id,
                        "resource_type": resource_type,
                        "status": resource.get("ResourceStatus", ""),
                    },
                    labels={
                        "aws": "true",
                        "cloudformation": "true",
                    },
                ))

            # Add edges for dependent resources
            # (Would require additional API calls to get dependencies)
            # For now, stack itself is a node
            nodes.append(Node(
                id=f"stack:{stack_name}",
                name=stack_name,
                type="cloudformation_stack",
                properties={
                    "region": self.region,
                },
                labels={"aws": "true"},
            ))

            return TopologyGraph(
                nodes=nodes,
                edges=edges,
                metadata={
                    "source": "cloudformation",
                    "stack_name": stack_name,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                },
            )

        except Exception as e:
            logger.error(f"CloudFormation collection failed: {e}")
            return TopologyGraph()


class TopologyIngestor:
    """
    Unified Topology Ingestor

    Collects topology from various sources and saves to Neo4j.
    """

    def __init__(self, config: Optional[TopologyIngestorConfig] = None):
        self.config = config or TopologyIngestorConfig()
        self._k8s: Optional[KubernetesIngestor] = None
        self._cloudformation: Optional[CloudFormationIngestor] = None
        self._neo4j_driver = None

    @property
    def k8s(self) -> Optional[KubernetesIngestor]:
        """Lazy initialization of Kubernetes ingestor"""
        if self._k8s is None and self.config.k8s_api_server:
            self._k8s = KubernetesIngestor(
                api_server=self.config.k8s_api_server,
                token=self.config.k8s_token,
                ca_cert=self.config.k8s_ca_cert,
            )
        return self._k8s

    @property
    def cloudformation(self) -> Optional[CloudFormationIngestor]:
        """Lazy initialization of CloudFormation ingestor"""
        if self._cloudformation is None and self.config.aws_region:
            self._cloudformation = CloudFormationIngestor(
                region=self.config.aws_region,
                access_key=self.config.aws_access_key or "",
                secret_key=self.config.aws_secret_key or "",
            )
        return self._cloudformation

    @property
    def neo4j_driver(self):
        """Lazy initialization of Neo4j driver"""
        if self._neo4j_driver is None and self.config.neo4j_uri:
            try:
                from neo4j import GraphDatabase
                self._neo4j_driver = GraphDatabase.driver(
                    self.config.neo4j_uri,
                    auth=(self.config.neo4j_user or "neo4j", self.config.neo4j_password or "neo4j"),
                )
            except ImportError:
                logger.warning("neo4j driver not installed")
        return self._neo4j_driver

    async def from_k8s(
        self,
        cluster_name: str,
        namespace: str = "default",
    ) -> TopologyGraph:
        """
        Collect topology from Kubernetes.

        Args:
            cluster_name: Name/identifier for the cluster
            namespace: Kubernetes namespace

        Returns:
            TopologyGraph
        """
        if not self.k8s:
            logger.warning("Kubernetes ingestor not configured")
            return TopologyGraph()

        topology = await self.k8s.collect(namespace=namespace)
        topology.metadata["cluster_name"] = cluster_name
        return topology

    async def from_cloud_formation(
        self,
        stack_name: str,
    ) -> TopologyGraph:
        """
        Collect topology from CloudFormation.

        Args:
            stack_name: CloudFormation stack name

        Returns:
            TopologyGraph
        """
        if not self.cloudformation:
            logger.warning("CloudFormation ingestor not configured")
            return TopologyGraph()

        return await self.cloudformation.collect(stack_name=stack_name)

    def save_to_neo4j(
        self,
        tenant_id: str,
        topology: TopologyGraph,
    ) -> dict[str, Any]:
        """
        Save topology to Neo4j.

        Args:
            tenant_id: Tenant identifier
            topology: TopologyGraph to save

        Returns:
            Summary dict
        """
        if not self.neo4j_driver:
            return {"error": "Neo4j driver not available"}

        stats = {
            "nodes_created": 0,
            "edges_created": 0,
            "tenant_id": tenant_id,
            "source": topology.metadata.get("source", "unknown"),
        }

        with self.neo4j_driver.session() as session:
            # Clear existing topology for this tenant/cluster
            cluster_name = topology.metadata.get("cluster_name", "default")
            session.run(
                """
                MATCH (n:TopologyNode {tenant_id: $tenant_id, cluster_name: $cluster_name})
                DETACH DELETE n
                """,
                tenant_id=tenant_id,
                cluster_name=cluster_name,
            )

            # Create nodes
            for node in topology.nodes:
                session.run(
                    """
                    CREATE (n:TopologyNode)
                    SET n = $properties
                    """,
                    properties={
                        "id": node.id,
                        "tenant_id": tenant_id,
                        "name": node.name,
                        "type": node.type,
                        "properties": node.properties,
                        "labels": node.labels,
                        "cluster_name": cluster_name,
                        **topology.metadata,
                    },
                )
                stats["nodes_created"] += 1

            # Create edges
            for edge in topology.edges:
                session.run(
                    """
                    MATCH (source:TopologyNode {id: $source_id, tenant_id: $tenant_id})
                    MATCH (target:TopologyNode {id: $target_id, tenant_id: $tenant_id})
                    CREATE (source)-[r:TOPOLOGY_RELATIONSHIP]->(target)
                    SET r = $properties
                    """,
                    source_id=edge.source,
                    target_id=edge.target,
                    tenant_id=tenant_id,
                    properties={
                        "type": edge.type,
                        "properties": edge.properties,
                    },
                )
                stats["edges_created"] += 1

        logger.info(f"Saved {stats['nodes_created']} nodes and {stats['edges_created']} edges to Neo4j")
        return stats

    async def collect_and_save(
        self,
        tenant_id: str,
        source: str,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Collect topology and save to Neo4j.

        Args:
            tenant_id: Tenant identifier
            source: Source type ("k8s" or "cloudformation")
            **kwargs: Source-specific arguments

        Returns:
            Summary dict
        """
        if source == "k8s":
            topology = await self.from_k8s(
                cluster_name=kwargs.get("cluster_name", "default"),
                namespace=kwargs.get("namespace", "default"),
            )
        elif source == "cloudformation":
            topology = await self.from_cloud_formation(
                stack_name=kwargs.get("stack_name", ""),
            )
        else:
            return {"error": f"Unknown source: {source}"}

        if not topology.nodes:
            return {"error": "No topology collected", "source": source}

        # Save to Neo4j
        save_stats = self.save_to_neo4j(tenant_id=tenant_id, topology=topology)

        return {
            **save_stats,
            "metadata": topology.metadata,
        }

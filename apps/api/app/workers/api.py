"""
API Endpoints for Data Collection and ML Training

Provides:
- Metric collection triggers
- Topology collection triggers
- Model training endpoints
- Model registry endpoints
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.modules.auth.models import TbUser
from core.auth import get_current_user
from app.workers import MetricCollector, TopologyIngestor
from schemas import ResponseEnvelope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workers", tags=["Data Collection & ML"])


def _get_ml_training_components():
    try:
        from app.services.ml.training_pipeline import (
            MLPipeline,
            TrainingConfig,
            generate_synthetic_training_data,
        )
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML training dependencies are not installed in this environment.",
        ) from exc
    return MLPipeline, TrainingConfig, generate_synthetic_training_data


def _get_model_registry():
    try:
        from app.services.ml.model_registry import ModelRegistry
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model registry dependencies are not installed in this environment.",
        ) from exc
    return ModelRegistry


# ============================================================================
# Request/Response Models
# ============================================================================

class MetricCollectionRequest(BaseModel):
    source: str = Field(..., description="Source type: prometheus or cloudwatch")
    query: str = Field(..., description="Query string (PromQL or JSON)")
    hours_back: int = Field(24, description="Hours of historical data")
    step_seconds: int = Field(60, description="Resolution in seconds")


class TopologyCollectionRequest(BaseModel):
    source: str = Field(..., description="Source type: k8s or cloudformation")
    cluster_name: Optional[str] = Field(None, description="Cluster name (for K8s)")
    namespace: str = Field("default", description="Kubernetes namespace")
    stack_name: Optional[str] = Field(None, description="CloudFormation stack name")


class ModelTrainingRequest(BaseModel):
    service: str = Field(..., description="Service name")
    model_type: str = Field("random_forest", description="Model type")
    training_samples: int = Field(1000, description="Number of training samples")
    use_synthetic: bool = Field(True, description="Use synthetic data")


class ModelActivationRequest(BaseModel):
    model_key: str = Field(..., description="Model to activate")


# ============================================================================
# Metric Collection Endpoints
# ============================================================================

@router.post("/metrics/collect", response_model=ResponseEnvelope)
async def collect_metrics(
    request: MetricCollectionRequest,
    background_tasks: BackgroundTasks,
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    **BATCH MODE**: Collect metrics and save to database.

    Use this for scheduled data collection to build historical dataset.

    Sources:
    - prometheus: Requires prometheus_url in query
    - cloudwatch: Query should be JSON with namespace, metric_name, dimensions

    Example (Prometheus):
    POST /workers/metrics/collect
    {
      "source": "prometheus",
      "query": "rate(http_requests_total[5m])",
      "hours_back": 24
    }

    Example (CloudWatch):
    POST /workers/metrics/collect
    {
      "source": "cloudwatch",
      "query": "{\"namespace\": \"AWS/EC2\", \"metric_name\": \"CPUUtilization\", \"dimensions\": {\"InstanceId\": \"i-xxx\"}}"
    }
    """
    tenant_id = current_user.tenant_id

    if request.source == "prometheus":
        collector = MetricCollector()
        result = await collector.collect_and_save(
            tenant_id=tenant_id,
            source=request.source,
            query=request.query,
            hours_back=request.hours_back,
            step_seconds=request.step_seconds,
        )
    elif request.source == "cloudwatch":
        collector = MetricCollector()
        result = await collector.collect_and_save(
            tenant_id=tenant_id,
            source=request.source,
            query=request.query,
            hours_back=request.hours_back,
            step_seconds=request.step_seconds,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown source: {request.source}",
        )

    if "error" in result:
        return ResponseEnvelope.error(result["error"])

    return ResponseEnvelope.success(
        data={
            **result,
            "tenant_id": tenant_id,
            "collected_at": str(result.get("timestamp", "")),
        }
    )


@router.post("/metrics/fetch", response_model=ResponseEnvelope)
async def fetch_metrics_realtime(
    request: MetricCollectionRequest,
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    **REAL-TIME MODE**: Fetch metrics directly without saving.

    Use this for on-demand simulation with latest data.

    Difference from /collect:
    - /collect: Saves to DB for future use (slower, but persistent)
    - /fetch: Returns immediately (faster, but not saved)

    Example (Prometheus):
    POST /workers/metrics/fetch
    {
      "source": "prometheus",
      "query": "rate(http_requests_total[5m])",
      "hours_back": 1
    }

    Example (CloudWatch):
    POST /workers/metrics/fetch
    {
      "source": "cloudwatch",
      "query": "{\"namespace\": \"AWS/EC2\", \"metric_name\": \"CPUUtilization\"}"
    }
    """
    tenant_id = current_user.tenant_id

    collector = MetricCollector()
    result = await collector.fetch_realtime(
        source=request.source,
        query=request.query,
        hours_back=request.hours_back,
        step_seconds=request.step_seconds,
    )

    if "error" in result:
        return ResponseEnvelope.error(result["error"])

    return ResponseEnvelope.success(
        data={
            **result,
            "tenant_id": tenant_id,
        }
    )


@router.get("/metrics/sources", response_model=ResponseEnvelope)
def get_metric_sources(
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Get available metric sources and their configuration status.

    Returns:
        List of sources with configuration status
    """
    from core.config import get_settings

    settings = get_settings()

    sources = {
        "prometheus": {
            "available": bool(settings.prometheus_url),
            "url": settings.prometheus_url or "Not configured",
        },
        "cloudwatch": {
            "available": bool(settings.aws_region),
            "region": settings.aws_region or "Not configured",
        },
        "datadog": {
            "available": False,
            "note": "Not implemented",
        },
    }

    return ResponseEnvelope.success(data=sources)


# ============================================================================
# Topology Collection Endpoints
# ============================================================================

@router.post("/topology/collect", response_model=ResponseEnvelope)
async def collect_topology(
    request: TopologyCollectionRequest,
    background_tasks: BackgroundTasks,
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Collect topology from external source.

    Sources:
    - k8s: Collects from Kubernetes API
    - cloudformation: Collects from AWS CloudFormation

    Example (K8s):
    POST /workers/topology/collect
    {
      "source": "k8s",
      "cluster_name": "prod-cluster",
      "namespace": "default"
    }

    Example (CloudFormation):
    POST /workers/topology/collect
    {
      "source": "cloudformation",
      "stack_name": "production-stack"
    }
    """
    tenant_id = current_user.tenant_id

    if request.source == "k8s":
        ingestor = TopologyIngestor()
        result = await ingestor.collect_and_save(
            tenant_id=tenant_id,
            source=request.source,
            cluster_name=request.cluster_name or "default",
            namespace=request.namespace,
        )
    elif request.source == "cloudformation":
        if not request.stack_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="stack_name required for cloudformation source",
            )
        ingestor = TopologyIngestor()
        result = await ingestor.collect_and_save(
            tenant_id=tenant_id,
            source=request.source,
            stack_name=request.stack_name,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown source: {request.source}",
        )

    if "error" in result:
        return ResponseEnvelope.error(result["error"])

    return ResponseEnvelope.success(
        data={
            **result,
            "tenant_id": tenant_id,
        }
    )


@router.get("/topology/sources", response_model=ResponseEnvelope)
def get_topology_sources(
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Get available topology sources and their configuration status.

    Returns:
        List of sources with configuration status
    """
    from core.config import get_settings

    settings = get_settings()

    sources = {
        "k8s": {
            "available": bool(settings.k8s_api_server),
            "api_server": settings.k8s_api_server or "Not configured",
        },
        "cloudformation": {
            "available": bool(settings.aws_region),
            "region": settings.aws_region or "Not configured",
        },
        "azure": {
            "available": False,
            "note": "Not implemented",
        },
    }

    return ResponseEnvelope.success(data=sources)


# ============================================================================
# ML Training Endpoints
# ============================================================================

@router.post("/ml/train", response_model=ResponseEnvelope)
def train_model(
    request: ModelTrainingRequest,
    background_tasks: BackgroundTasks,
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Train ML model for simulation.

    Trains a surrogate model for KPI prediction.

    Example:
    POST /workers/ml/train
    {
      "service": "api-server",
      "model_type": "random_forest",
      "training_samples": 1000,
      "use_synthetic": true
    }
    """
    tenant_id = current_user.tenant_id
    MLPipeline, TrainingConfig, generate_synthetic_training_data = _get_ml_training_components()

    # Prepare training data
    if request.use_synthetic:
        # Generate synthetic data for testing
        data = generate_synthetic_training_data(n_samples=request.training_samples)
    else:
        # Load from metric timeseries
        # This would require actual data in the database
        from app.modules.simulation.services.simulation.metric_loader import _get_metric_timeseries
        from core.db import get_session_context

        with get_session_context() as session:
            metric_data = _get_metric_timeseries(
                session=session,
                tenant_id=tenant_id,
                service=request.service,
                hours_back=168,  # 7 days
            )

        if not any(metric_data.values()):
            return ResponseEnvelope.error(
                "No metric data available. Set use_synthetic=true to train with synthetic data."
            )

        # This would require more complex ETL
        return ResponseEnvelope.error(
            "Training from real data not fully implemented. Use use_synthetic=true."
        )

    # Train model
    try:
        pipeline = MLPipeline(
            config=TrainingConfig(
                model_type=request.model_type,
                n_estimators=100,
            )
        )

        metadata = pipeline.train_surrogate_model(
            tenant_id=tenant_id,
            service=request.service,
            historical_data=data,
            log_to_mlflow=False,
        )

        return ResponseEnvelope.success(
            data={
                "model_key": metadata.model_key,
                "version": metadata.version,
                "metrics": metadata.metrics.model_dump(),
                "feature_names": metadata.feature_names,
                "target_names": metadata.target_names,
                "training_samples": metadata.training_samples,
                "tenant_id": tenant_id,
            }
        )

    except Exception as e:
        logger.error(f"Model training failed: {e}")
        return ResponseEnvelope.error(f"Training failed: {str(e)}")


@router.get("/ml/models", response_model=ResponseEnvelope)
def list_models(
    service: Optional[str] = None,
    model_type: Optional[str] = None,
    limit: int = 50,
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    List registered ML models.

    Query Parameters:
    - service: Filter by service
    - model_type: Filter by model type
    - limit: Max results (default: 50)
    """
    tenant_id = current_user.tenant_id

    ModelRegistry = _get_model_registry()
    registry = ModelRegistry()
    models = registry.list_models(
        tenant_id=tenant_id,
        service=service,
        model_type=model_type,
        limit=limit,
    )

    return ResponseEnvelope.success(
        data={
            "models": [m.model_dump() for m in models],
            "count": len(models),
            "tenant_id": tenant_id,
        }
    )


@router.get("/ml/models/active", response_model=ResponseEnvelope)
def get_active_model(
    service: str,
    model_type: str = "surrogate",
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Get active model for a service.

    Query Parameters:
    - service: Service name (required)
    - model_type: Model type (default: surrogate)
    """
    tenant_id = current_user.tenant_id

    ModelRegistry = _get_model_registry()
    registry = ModelRegistry()
    model_info = registry.get_active_model(
        tenant_id=tenant_id,
        service=service,
        model_type=model_type,
    )

    if not model_info:
        return ResponseEnvelope.error(
            f"No active model found for {service} (type: {model_type})"
        )

    return ResponseEnvelope.success(
        data={
            **model_info.model_dump(),
            "tenant_id": tenant_id,
        }
    )


@router.post("/ml/models/activate", response_model=ResponseEnvelope)
def activate_model(
    request: ModelActivationRequest,
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Activate a model.

    Example:
    POST /workers/ml/models/activate
    {
      "model_key": "tenant1:api-server:random_forest:20240211_120000"
    }
    """
    ModelRegistry = _get_model_registry()
    registry = ModelRegistry()
    success = registry.activate_model(request.model_key)

    if not success:
        return ResponseEnvelope.error(
            f"Failed to activate model: {request.model_key}"
        )

    return ResponseEnvelope.success(
        data={
            "model_key": request.model_key,
            "activated": True,
        }
    )


@router.delete("/ml/models/{model_key}", response_model=ResponseEnvelope)
def delete_model(
    model_key: str,
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Delete a model from registry."""
    ModelRegistry = _get_model_registry()
    registry = ModelRegistry()
    success = registry.delete_model(model_key)

    if not success:
        return ResponseEnvelope.error(
            f"Failed to delete model: {model_key}"
        )

    return ResponseEnvelope.success(
        data={
            "model_key": model_key,
            "deleted": True,
        }
    )


# ============================================================================
# Health/Status Endpoints
# ============================================================================

@router.get("/status", response_model=ResponseEnvelope)
def get_workers_status(
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Get status of data collection workers.

    Returns:
        Worker status and configuration info
    """
    from core.config import get_settings

    settings = get_settings()

    status = {
        "metric_collection": {
            "prometheus": bool(settings.prometheus_url),
            "cloudwatch": bool(settings.aws_region),
        },
        "topology_collection": {
            "k8s": bool(settings.k8s_api_server),
            "cloudformation": bool(settings.aws_region),
        },
        "ml_training": {
            "enabled": True,
            "mlflow_available": False,  # Check dynamically
        },
        "database": {
            "postgres": True,
            "neo4j": bool(settings.neo4j_uri),
        },
    }

    return ResponseEnvelope.success(data=status)

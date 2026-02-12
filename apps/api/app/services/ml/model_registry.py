"""
ML Model Registry for Simulation System

Provides:
- Model metadata storage (SQLModel)
- Model loading and retrieval
- Model versioning
- Active model management
"""
from __future__ import annotations

import json
import logging
import pickle
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlmodel import Column, Field as SQLField, SQLModel, Text

logger = logging.getLogger(__name__)


class TbMLModel(SQLModel, table=True):
    """
    ML Model Registry Table

    Stores trained model metadata and serialized model blobs.
    """
    __tablename__ = "tb_ml_models"

    id: Optional[int] = SQLField(default=None, primary_key=True)
    model_key: str = SQLField(index=True)
    tenant_id: str = SQLField(index=True)
    service: str = SQLField(index=True)
    model_type: str = SQLField(index=True)  # ml, dl, surrogate
    version: str = SQLField(index=True)

    # Model storage (pickled bytes)
    model_blob: bytes = SQLField(Column(Text))

    # Metadata
    is_active: bool = SQLField(default=True, index=True)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    feature_names: str = SQLField(Text)  # JSON array
    target_names: str = SQLField(Text)  # JSON array

    # Performance metrics
    r2_score: float
    mape: float
    rmse: float
    mae: float
    coverage_90: float

    # Training info
    training_samples: int
    training_config: str = SQLField(Text)  # JSON object

    # Additional metadata
    tags: str = SQLField(Text, default="{}")  # JSON object
    notes: str = SQLField(Text, default="")


class ModelInfo(BaseModel):
    """Model information summary"""
    model_key: str
    tenant_id: str
    service: str
    model_type: str
    version: str
    is_active: bool
    created_at: datetime
    metrics: dict[str, float]
    training_samples: int
    feature_names: list[str]
    target_names: list[str]


class ModelRegistry:
    """
    ML Model Registry

    Manages model lifecycle: registration, retrieval, activation.
    """

    def register_model(
        self,
        tenant_id: str,
        service: str,
        model: Any,
        model_type: str,
        metrics: dict[str, float],
        feature_names: list[str],
        target_names: list[str],
        training_samples: int,
        training_config: dict[str, Any],
        tags: Optional[dict[str, str]] = None,
        notes: str = "",
    ) -> str:
        """
        Register a new model in the registry.

        Args:
            tenant_id: Tenant identifier
            service: Service name
            model: Trained model object (must be pickleable)
            model_type: Model type (ml, dl, surrogate)
            metrics: Performance metrics dict
            feature_names: List of feature names
            target_names: List of target names
            training_samples: Number of training samples
            training_config: Training configuration dict
            tags: Optional tags dict
            notes: Optional notes

        Returns:
            model_key (unique identifier)
        """
        from core.db import get_session_context

        # Generate version
        version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        model_key = f"{tenant_id}:{service}:{model_type}:{version}"

        # Serialize model
        model_blob = pickle.dumps(model)

        with get_session_context() as session:
            # Deactivate previous models
            session.query(TbMLModel).filter(
                TbMLModel.tenant_id == tenant_id,
                TbMLModel.service == service,
                TbMLModel.model_type == model_type,
            ).update({"is_active": False})

            # Create new model record
            db_model = TbMLModel(
                model_key=model_key,
                tenant_id=tenant_id,
                service=service,
                model_type=model_type,
                version=version,
                model_blob=model_blob,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                feature_names=json.dumps(feature_names),
                target_names=json.dumps(target_names),
                r2_score=metrics.get("r2_score", 0.0),
                mape=metrics.get("mape", 100.0),
                rmse=metrics.get("rmse", 999.0),
                mae=metrics.get("mae", 999.0),
                coverage_90=metrics.get("coverage_90", 0.0),
                training_samples=training_samples,
                training_config=json.dumps(training_config),
                tags=json.dumps(tags or {}),
                notes=notes,
            )

            session.add(db_model)
            session.commit()

        logger.info(f"Registered model: {model_key}")
        return model_key

    def load_model(
        self,
        model_key: str,
    ) -> Optional[Any]:
        """
        Load a model by key.

        Args:
            model_key: Unique model identifier

        Returns:
            Deserialized model object or None if not found
        """
        from core.db import get_session_context

        with get_session_context() as session:
            db_model = session.query(TbMLModel).filter(
                TbMLModel.model_key == model_key
            ).first()

            if not db_model:
                logger.warning(f"Model not found: {model_key}")
                return None

            try:
                model = pickle.loads(db_model.model_blob)
                logger.info(f"Loaded model: {model_key}")
                return model
            except Exception as e:
                logger.error(f"Failed to deserialize model {model_key}: {e}")
                return None

    def get_active_model(
        self,
        tenant_id: str,
        service: str,
        model_type: str = "surrogate",
    ) -> Optional[ModelInfo]:
        """
        Get the active model for a tenant/service.

        Args:
            tenant_id: Tenant identifier
            service: Service name
            model_type: Model type filter

        Returns:
            ModelInfo or None if not found
        """
        from core.db import get_session_context

        with get_session_context() as session:
            db_model = session.query(TbMLModel).filter(
                TbMLModel.tenant_id == tenant_id,
                TbMLModel.service == service,
                TbMLModel.model_type == model_type,
                TbMLModel.is_active == True,
            ).order_by(TbMLModel.created_at.desc()).first()

            if not db_model:
                return None

            return ModelInfo(
                model_key=db_model.model_key,
                tenant_id=db_model.tenant_id,
                service=db_model.service,
                model_type=db_model.model_type,
                version=db_model.version,
                is_active=db_model.is_active,
                created_at=db_model.created_at,
                metrics={
                    "r2_score": db_model.r2_score,
                    "mape": db_model.mape,
                    "rmse": db_model.rmse,
                    "mae": db_model.mae,
                    "coverage_90": db_model.coverage_90,
                },
                training_samples=db_model.training_samples,
                feature_names=json.loads(db_model.feature_names),
                target_names=json.loads(db_model.target_names),
            )

    def list_models(
        self,
        tenant_id: str,
        service: Optional[str] = None,
        model_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[ModelInfo]:
        """
        List models for a tenant.

        Args:
            tenant_id: Tenant identifier
            service: Optional service filter
            model_type: Optional model type filter
            limit: Max results

        Returns:
            List of ModelInfo
        """
        from core.db import get_session_context

        with get_session_context() as session:
            query = session.query(TbMLModel).filter(
                TbMLModel.tenant_id == tenant_id
            )

            if service:
                query = query.filter(TbMLModel.service == service)
            if model_type:
                query = query.filter(TbMLModel.model_type == model_type)

            results = query.order_by(TbMLModel.created_at.desc()).limit(limit).all()

            return [
                ModelInfo(
                    model_key=m.model_key,
                    tenant_id=m.tenant_id,
                    service=m.service,
                    model_type=m.model_type,
                    version=m.version,
                    is_active=m.is_active,
                    created_at=m.created_at,
                    metrics={
                        "r2_score": m.r2_score,
                        "mape": m.mape,
                        "rmse": m.rmse,
                        "mae": m.mae,
                        "coverage_90": m.coverage_90,
                    },
                    training_samples=m.training_samples,
                    feature_names=json.loads(m.feature_names),
                    target_names=json.loads(m.target_names),
                )
                for m in results
            ]

    def activate_model(
        self,
        model_key: str,
    ) -> bool:
        """
        Activate a model (deactivates others of same type).

        Args:
            model_key: Model to activate

        Returns:
            True if successful
        """
        from core.db import get_session_context

        with get_session_context() as session:
            # Find the model
            model = session.query(TbMLModel).filter(
                TbMLModel.model_key == model_key
            ).first()

            if not model:
                logger.warning(f"Model not found for activation: {model_key}")
                return False

            # Deactivate same-type models for this tenant/service
            session.query(TbMLModel).filter(
                TbMLModel.tenant_id == model.tenant_id,
                TbMLModel.service == model.service,
                TbMLModel.model_type == model.model_type,
                TbMLModel.model_key != model_key,
            ).update({"is_active": False})

            # Activate this model
            model.is_active = True
            session.commit()

            logger.info(f"Activated model: {model_key}")
            return True

    def delete_model(
        self,
        model_key: str,
    ) -> bool:
        """
        Delete a model from registry.

        Args:
            model_key: Model to delete

        Returns:
            True if successful
        """
        from core.db import get_session_context

        with get_session_context() as session:
            model = session.query(TbMLModel).filter(
                TbMLModel.model_key == model_key
            ).first()

            if not model:
                logger.warning(f"Model not found for deletion: {model_key}")
                return False

            session.delete(model)
            session.commit()

            logger.info(f"Deleted model: {model_key}")
            return True


# Convenience functions for common operations
def get_active_model_for_service(
    tenant_id: str,
    service: str,
) -> Optional[Any]:
    """
    Convenience function to get active model for a service.

    Returns:
        Deserialized model object or None
    """
    registry = ModelRegistry()
    model_info = registry.get_active_model(tenant_id, service, "surrogate")

    if not model_info:
        return None

    return registry.load_model(model_info.model_key)

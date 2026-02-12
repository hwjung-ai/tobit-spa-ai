"""
ML Model Training Pipeline for Simulation System

Provides:
- Surrogate model training (RandomForest, GradientBoosting)
- Model evaluation (R², MAPE, RMSE)
- Model serialization and storage
- MLflow integration (optional)
"""
from __future__ import annotations

import io
import json
import logging
import pickle
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from core.db import get_session_context

logger = logging.getLogger(__name__)


class TrainingConfig(BaseModel):
    """Configuration for model training"""
    model_type: str = "random_forest"  # random_forest, gradient_boosting, xgboost
    test_size: float = 0.2
    random_state: int = 42
    n_estimators: int = 100
    max_depth: Optional[int] = None
    learning_rate: float = 0.1
    cross_validation_folds: int = 5


class ModelMetrics(BaseModel):
    """Model evaluation metrics"""
    r2_score: float
    mape: float  # Mean Absolute Percentage Error
    rmse: float  # Root Mean Squared Error
    mae: float  # Mean Absolute Error
    coverage_90: float  # % of actual values within 90% prediction interval


class ModelMetadata(BaseModel):
    """Metadata for trained model"""
    model_key: str
    tenant_id: str
    service: str
    model_type: str  # ml, dl, surrogate
    version: str
    created_at: datetime
    is_active: bool = True
    training_samples: int
    feature_names: list[str]
    target_names: list[str]
    metrics: ModelMetrics
    training_config: dict[str, Any]


class MLPipeline:
    """
    ML Model Training Pipeline

    Trains surrogate models for simulation KPI prediction.

    Features:
    - traffic_change_pct
    - cpu_change_pct
    - memory_change_pct
    - latency_ms (baseline)
    - throughput_rps (baseline)
    - error_rate_pct (baseline)
    - cost_usd_hour (baseline)

    Targets:
    - latency_ms (simulated)
    - throughput_rps (simulated)
    - error_rate_pct (simulated)
    - cost_usd_hour (simulated)
    """

    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self._model = None
        self._scaler = None

    def _prepare_features(
        self,
        historical_data: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare feature and target matrices from historical data.

        Expected columns in historical_data:
        - traffic_change_pct, cpu_change_pct, memory_change_pct (inputs)
        - latency_ms, throughput_rps, error_rate_pct, cost_usd_hour (baseline)
        - sim_latency_ms, sim_throughput_rps, sim_error_rate_pct, sim_cost_usd_hour (targets)

        Returns:
            (X, y) where X is features, y is targets
        """
        # Feature columns
        feature_cols = [
            "traffic_change_pct",
            "cpu_change_pct",
            "memory_change_pct",
            "latency_ms",
            "throughput_rps",
            "error_rate_pct",
            "cost_usd_hour",
        ]

        # Target columns (simulated values)
        target_cols = [
            "sim_latency_ms",
            "sim_throughput_rps",
            "sim_error_rate_pct",
            "sim_cost_usd_hour",
        ]

        # Check if columns exist
        missing_features = [c for c in feature_cols if c not in historical_data.columns]
        missing_targets = [c for c in target_cols if c not in historical_data.columns]

        if missing_features:
            logger.warning(f"Missing feature columns: {missing_features}")
            # Create default features
            for col in missing_features:
                if "change_pct" in col:
                    historical_data[col] = 0.0
                else:
                    historical_data[col] = historical_data.get(col.replace("sim_", ""), 0.0)

        if missing_targets:
            logger.warning(f"Missing target columns: {missing_targets}")
            # Create synthetic targets (baseline + small variation)
            for col in missing_targets:
                base_col = col.replace("sim_", "")
                if base_col in historical_data.columns:
                    historical_data[col] = historical_data[base_col] * (1 + np.random.normal(0, 0.05))
                else:
                    historical_data[col] = 0.0

        X = historical_data[feature_cols].copy()
        y = historical_data[target_cols].copy()

        # Handle missing values
        X = X.fillna(0)
        y = y.fillna(0)

        return X, y

    def _train_model(self, X: pd.DataFrame, y: pd.DataFrame) -> Any:
        """
        Train the ML model based on config.

        Returns:
            Trained model object
        """
        model_type = self.config.model_type.lower()

        if model_type == "random_forest":
            from sklearn.ensemble import RandomForestRegressor
            model = RandomForestRegressor(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                random_state=self.config.random_state,
                n_jobs=-1,
            )
        elif model_type == "gradient_boosting":
            from sklearn.ensemble import GradientBoostingRegressor
            model = GradientBoostingRegressor(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                learning_rate=self.config.learning_rate,
                random_state=self.config.random_state,
            )
        elif model_type == "xgboost":
            try:
                import xgboost as xgb
                model = xgb.XGBRegressor(
                    n_estimators=self.config.n_estimators,
                    max_depth=self.config.max_depth or 6,
                    learning_rate=self.config.learning_rate,
                    random_state=self.config.random_state,
                )
            except ImportError:
                logger.warning("XGBoost not installed, falling back to RandomForest")
                from sklearn.ensemble import RandomForestRegressor
                model = RandomForestRegressor(
                    n_estimators=self.config.n_estimators,
                    random_state=self.config.random_state,
                )
        else:
            logger.warning(f"Unknown model type: {model_type}, using RandomForest")
            from sklearn.ensemble import RandomForestRegressor
            model = RandomForestRegressor(
                n_estimators=self.config.n_estimators,
                random_state=self.config.random_state,
            )

        # Train multi-output model
        model.fit(X, y)
        return model

    def _evaluate_model(
        self,
        model: Any,
        X_test: pd.DataFrame,
        y_test: pd.DataFrame,
    ) -> ModelMetrics:
        """
        Evaluate model performance.

        Returns:
            ModelMetrics with R², MAPE, RMSE, MAE, Coverage@90
        """
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        # Predict
        y_pred = model.predict(X_test)

        # Calculate metrics per target, then average
        r2_scores = []
        mapes = []
        rmses = []
        maes = []
        coverage_90s = []

        for i, col in enumerate(y_test.columns):
            y_true_i = y_test.iloc[:, i].values
            y_pred_i = y_pred[:, i] if len(y_pred.shape) > 1 else y_pred

            # R²
            r2 = r2_score(y_true_i, y_pred_i)
            r2_scores.append(r2)

            # MAPE (avoid division by zero)
            mask = np.abs(y_true_i) > 1e-6
            if mask.sum() > 0:
                mape = np.mean(np.abs((y_true_i[mask] - y_pred_i[mask]) / y_true_i[mask])) * 100
            else:
                mape = 100.0
            mapes.append(mape)

            # RMSE
            rmse = np.sqrt(mean_squared_error(y_true_i, y_pred_i))
            rmses.append(rmse)

            # MAE
            mae = mean_absolute_error(y_true_i, y_pred_i)
            maes.append(mae)

            # Coverage@90 (simple heuristic: std * 1.645)
            std = np.std(y_true_i - y_pred_i)
            margin = 1.645 * std
            within_range = np.abs(y_true_i - y_pred_i) <= margin
            coverage_90s.append(np.mean(within_range) * 100)

        return ModelMetrics(
            r2_score=float(np.mean(r2_scores)),
            mape=float(np.mean(mapes)),
            rmse=float(np.mean(rmses)),
            mae=float(np.mean(maes)),
            coverage_90=float(np.mean(coverage_90s)),
        )

    def train_surrogate_model(
        self,
        tenant_id: str,
        service: str,
        historical_data: pd.DataFrame,
        log_to_mlflow: bool = False,
    ) -> ModelMetadata:
        """
        Train surrogate model for simulation.

        Args:
            tenant_id: Tenant identifier
            service: Service name
            historical_data: DataFrame with features and targets
            log_to_mlflow: Whether to log to MLflow

        Returns:
            ModelMetadata with trained model info
        """
        # Prepare data
        X, y = self._prepare_features(historical_data)

        # Train/test split
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.config.test_size,
            random_state=self.config.random_state,
        )

        # Train model
        model = self._train_model(X_train, y_train)

        # Evaluate
        metrics = self._evaluate_model(model, X_test, y_test)

        # Generate model metadata
        version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        model_key = f"{tenant_id}:{service}:{self.config.model_type}:{version}"

        metadata = ModelMetadata(
            model_key=model_key,
            tenant_id=tenant_id,
            service=service,
            model_type="surrogate",
            version=version,
            created_at=datetime.now(timezone.utc),
            training_samples=len(historical_data),
            feature_names=list(X.columns),
            target_names=list(y.columns),
            metrics=metrics,
            training_config=self.config.model_dump(),
        )

        # Serialize model
        model_blob = pickle.dumps(model)

        # Save to database
        self._save_model_to_db(metadata, model_blob)

        # Optional: Log to MLflow
        if log_to_mlflow:
            self._log_to_mlflow(model, metadata, metrics)

        logger.info(
            f"Trained surrogate model for {service}: "
            f"R²={metrics.r2_score:.3f}, MAPE={metrics.mape:.2f}%"
        )

        return metadata

    def _save_model_to_db(
        self,
        metadata: ModelMetadata,
        model_blob: bytes,
    ) -> None:
        """Save model metadata and blob to database"""
        from app.services.ml.model_registry import TbMLModel

        with get_session_context() as session:
            # Deactivate old models for this tenant/service
            session.query(TbMLModel).filter(
                TbMLModel.tenant_id == metadata.tenant_id,
                TbMLModel.service == metadata.service,
                TbMLModel.model_type == metadata.model_type,
            ).update({"is_active": False})

            # Create new model record
            db_model = TbMLModel(
                model_key=metadata.model_key,
                tenant_id=metadata.tenant_id,
                service=metadata.service,
                model_type=metadata.model_type,
                version=metadata.version,
                model_blob=model_blob,
                is_active=True,
                feature_names=json.dumps(metadata.feature_names),
                target_names=json.dumps(metadata.target_names),
                r2_score=metadata.metrics.r2_score,
                mape=metadata.metrics.mape,
                rmse=metadata.metrics.rmse,
                mae=metadata.metrics.mae,
                coverage_90=metadata.metrics.coverage_90,
                training_samples=metadata.training_samples,
                training_config=json.dumps(metadata.training_config),
            )

            session.add(db_model)
            session.commit()

    def _log_to_mlflow(
        self,
        model: Any,
        metadata: ModelMetadata,
        metrics: ModelMetrics,
    ) -> None:
        """Log model to MLflow (if available)"""
        try:
            import mlflow
            import mlflow.sklearn

            with mlflow.start_run():
                mlflow.log_params(metadata.training_config)
                mlflow.log_metrics({
                    "r2_score": metrics.r2_score,
                    "mape": metrics.mape,
                    "rmse": metrics.rmse,
                    "mae": metrics.mae,
                    "coverage_90": metrics.coverage_90,
                })
                mlflow.sklearn.log_model(model, "model")
                mlflow.set_tag("service", metadata.service)
                mlflow.set_tag("tenant_id", metadata.tenant_id)

            logger.info(f"Logged model to MLflow: {metadata.model_key}")
        except ImportError:
            logger.warning("MLflow not installed")
        except Exception as e:
            logger.error(f"Failed to log to MLflow: {e}")


def generate_synthetic_training_data(
    n_samples: int = 1000,
    noise_level: float = 0.1,
) -> pd.DataFrame:
    """
    Generate synthetic training data for model testing.

    Creates realistic simulation scenarios with inputs and expected outputs.

    Args:
        n_samples: Number of samples to generate
        noise_level: Noise level to add (0-1)

    Returns:
        DataFrame with feature and target columns
    """
    np.random.seed(42)

    # Generate features
    traffic_change = np.random.uniform(-50, 100, n_samples)  # -50% to +100%
    cpu_change = np.random.uniform(-30, 50, n_samples)
    memory_change = np.random.uniform(-20, 40, n_samples)

    # Baseline values
    baseline_latency = np.random.normal(50, 10, n_samples)
    baseline_throughput = np.random.normal(1000, 200, n_samples)
    baseline_error_rate = np.random.normal(0.5, 0.2, n_samples)
    baseline_cost = np.random.normal(10, 2, n_samples)

    # Apply formula-based transformations with noise
    # Latency increases nonlinearly with traffic and CPU
    sim_latency = baseline_latency * (
        1 + 0.003 * traffic_change + 0.002 * cpu_change
    ) * np.random.normal(1, noise_level, n_samples)

    # Throughput scales roughly with traffic
    sim_throughput = baseline_throughput * (
        1 + 0.008 * traffic_change
    ) * np.random.normal(1, noise_level * 0.5, n_samples)

    # Error rate increases exponentially with load
    load_factor = (traffic_change / 100 + cpu_change / 100) / 2
    sim_error_rate = baseline_error_rate * (
        1 + 2 * load_factor + load_factor ** 2
    ) * np.random.normal(1, noise_level, n_samples)

    # Cost scales with CPU/memory (resource usage)
    sim_cost = baseline_cost * (
        1 + 0.004 * cpu_change + 0.003 * memory_change
    ) * np.random.normal(1, noise_level * 0.5, n_samples)

    return pd.DataFrame({
        "traffic_change_pct": traffic_change,
        "cpu_change_pct": cpu_change,
        "memory_change_pct": memory_change,
        "latency_ms": baseline_latency,
        "throughput_rps": baseline_throughput,
        "error_rate_pct": baseline_error_rate,
        "cost_usd_hour": baseline_cost,
        "sim_latency_ms": sim_latency,
        "sim_throughput_rps": sim_throughput,
        "sim_error_rate_pct": sim_error_rate,
        "sim_cost_usd_hour": sim_cost,
    })

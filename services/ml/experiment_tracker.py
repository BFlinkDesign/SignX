"""MLflow experiment tracking integration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import mlflow
import structlog

logger = structlog.get_logger(__name__)


class ExperimentTracker:
    """MLflow wrapper for tracking cost model experiments."""
    
    def __init__(self, experiment_name: str = "signx-cost-prediction"):
        """Initialize experiment tracker.
        
        Args:
            experiment_name: Name of MLflow experiment
        """
        self.experiment_name = experiment_name
        
        # Set tracking URI
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
        mlflow.set_tracking_uri(tracking_uri)
        
        # Create or get experiment
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(experiment_name)
                logger.info("mlflow.experiment.created", 
                           name=experiment_name,
                           id=experiment_id)
            else:
                mlflow.set_experiment(experiment_name)
                logger.info("mlflow.experiment.loaded", name=experiment_name)
        except Exception as e:
            logger.warning("mlflow.setup.failed", error=str(e))
    
    def log_training_run(
        self,
        model: Any,
        metrics: dict[str, float],
        params: dict[str, Any],
        artifacts: Optional[list[Path]] = None,
        tags: Optional[dict[str, str]] = None,
    ) -> str:
        """Log a training run to MLflow.
        
        Args:
            model: Trained model object
            metrics: Training metrics to log
            params: Hyperparameters to log
            artifacts: Optional list of artifact paths to log
            tags: Optional tags for the run
            
        Returns:
            MLflow run ID
        """
        with mlflow.start_run() as run:
            # Log parameters
            for key, value in params.items():
                mlflow.log_param(key, value)
            
            # Log metrics
            for key, value in metrics.items():
                mlflow.log_metric(key, value)
            
            # Log tags
            if tags:
                mlflow.set_tags(tags)
            
            # Log model
            try:
                mlflow.sklearn.log_model(model, "model")
            except Exception as e:
                logger.warning("mlflow.log_model.failed", error=str(e))
            
            # Log artifacts
            if artifacts:
                for artifact_path in artifacts:
                    if Path(artifact_path).exists():
                        mlflow.log_artifact(str(artifact_path))
            
            run_id = run.info.run_id
            
            logger.info("mlflow.run.logged",
                       run_id=run_id,
                       metrics_count=len(metrics))
            
            return run_id
    
    def compare_runs(self, metric: str = "test_mae", top_n: int = 5) -> list[dict]:
        """Compare top N runs by specified metric.
        
        Args:
            metric: Metric to sort by
            top_n: Number of top runs to return
            
        Returns:
            List of run dictionaries sorted by metric
        """
        experiment = mlflow.get_experiment_by_name(self.experiment_name)
        if experiment is None:
            return []
        
        # Search runs
        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=[f"metrics.{metric} ASC"],
            max_results=top_n,
        )
        
        return runs.to_dict(orient="records")


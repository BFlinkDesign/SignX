"""
APEX Signage Engineering - Batch Processing

Parallel processing for multiple project configurations.
"""

from __future__ import annotations

import multiprocessing
from typing import Any, Callable, Dict, List, Optional

from .models import Cabinet, SiteLoads


# ========== Batch Solver ==========


class ProjectConfig:
    """Configuration for a single project in batch."""
    
    def __init__(
        self,
        project_id: str,
        site: SiteLoads,
        cabinets: List[Dict[str, Any]],
        height_ft: float,
    ):
        self.project_id = project_id
        self.site = site
        self.cabinets = cabinets
        self.height_ft = height_ft


def _solve_single_project(config: ProjectConfig) -> Dict[str, Any]:
    """
    Solve a single project (used in multiprocessing).
    
    Args:
        config: Project configuration
    
    Returns:
        Dict with project_id, result, error (if any)
    """
    try:
        from .solvers import derive_loads
        
        # Convert dicts to Cabinet objects
        cabinet_objs = [
            Cabinet(
                width_ft=c["width_ft"],
                height_ft=c["height_ft"],
                depth_in=c.get("depth_in", 12.0),
                weight_psf=c.get("weight_psf", 10.0),
            )
            for c in config.cabinets
        ]
        
        # Derive loads
        result = derive_loads(config.site, cabinet_objs, config.height_ft, seed=0)
        
        return {
            "project_id": config.project_id,
            "result": {
                "a_ft2": result.a_ft2,
                "z_cg_ft": result.z_cg_ft,
                "weight_estimate_lb": result.weight_estimate_lb,
                "mu_kipft": result.mu_kipft,
            },
            "error": None,
        }
    except Exception as e:
        return {
            "project_id": config.project_id,
            "result": None,
            "error": str(e),
        }


def solve_batch(
    projects: List[ProjectConfig],
    progress_callback: Optional[Callable[[int, int, int], None]] = None,
    n_workers: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Solve multiple projects in parallel.
    
    Args:
        projects: List of project configurations
        progress_callback: Optional callback(total, completed, failed)
        n_workers: Number of parallel workers (default: CPU count)
    
    Returns:
        List of results (one per project)
    
    Target: Process 100 projects in <10s
    """
    n_workers = n_workers or min(multiprocessing.cpu_count(), 8)  # Cap at 8 workers
    
    if len(projects) == 0:
        return []
    
    if len(projects) == 1:
        # Single project, no need for multiprocessing
        result = _solve_single_project(projects[0])
        if progress_callback:
            progress_callback(1, 1, 0 if result["error"] is None else 1)
        return [result]
    
    # Use multiprocessing pool
    with multiprocessing.Pool(processes=n_workers) as pool:
        results = []
        completed = 0
        failed = 0
        
        # Process in batches to allow progress updates
        batch_size = max(10, len(projects) // 10)  # 10 batches
        
        for i in range(0, len(projects), batch_size):
            batch = projects[i : i + batch_size]
            batch_results = pool.map(_solve_single_project, batch)
            
            results.extend(batch_results)
            completed += len(batch_results)
            failed += sum(1 for r in batch_results if r["error"] is not None)
            
            if progress_callback:
                progress_callback(len(projects), completed, failed)
    
    return results


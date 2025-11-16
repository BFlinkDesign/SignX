"""Tests for structure graph generation."""

import pytest
import torch

from ..structure_graph import StructureGraph


def test_create_pole_graph_basic():
    """Test basic pole graph creation."""
    graph = StructureGraph.create_pole_graph(
        pole_height_ft=20.0,
        pole_diameter_in=8.0,
        sign_height_ft=6.0,
        sign_width_ft=10.0,
        wind_force_lbs=1500.0,
        dead_load_lbs=500.0,
        material_properties={
            "E": 29000.0,
            "fy": 46.0,
            "area": 8.36,
            "Ix": 57.5,
            "Iy": 57.5,
        },
        n_segments=5,
    )
    
    # Check graph structure
    assert graph.num_nodes == 6  # 5 segments + 1 = 6 nodes
    assert graph.x.shape[0] == 6
    assert graph.x.shape[1] == 10  # 10 features per node
    assert graph.edge_index.shape[1] == 10  # 5 segments × 2 (bidirectional)
    
    # Check features are reasonable
    assert torch.all(graph.x[:, 2] >= 0)  # Z positions non-negative
    assert torch.all(graph.x[:, 2] <= 20.0)  # Z positions <= height


def test_add_target_values():
    """Test adding target values for supervised learning."""
    graph = StructureGraph.create_pole_graph(
        pole_height_ft=20.0,
        pole_diameter_in=8.0,
        sign_height_ft=6.0,
        sign_width_ft=10.0,
        wind_force_lbs=1500.0,
        dead_load_lbs=500.0,
        material_properties={"E": 29000, "fy": 46, "area": 8.36, "Ix": 57.5, "Iy": 57.5},
        n_segments=5,
    )
    
    # Add targets
    stress_vals = [1000, 900, 800, 700, 600, 500]
    deflection_vals = [0, 0.1, 0.3, 0.6, 1.0, 1.5]
    
    graph = StructureGraph.add_target_values(graph, stress_vals, deflection_vals)
    
    assert hasattr(graph, "y_stress")
    assert hasattr(graph, "y_deflection")
    assert graph.y_stress.shape[0] == 6
    assert graph.y_deflection.shape[0] == 6


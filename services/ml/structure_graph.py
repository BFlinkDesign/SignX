"""Structure graph representation for Graph Neural Networks.

Converts sign pole structures into PyTorch Geometric graph format
for future GNN-based stress prediction and optimization.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import torch
from torch_geometric.data import Data

import structlog

logger = structlog.get_logger(__name__)


class StructureGraph:
    """Convert pole structure to graph representation for GNN processing."""
    
    @staticmethod
    def create_pole_graph(
        pole_height_ft: float,
        pole_diameter_in: float,
        sign_height_ft: float,
        sign_width_ft: float,
        wind_force_lbs: float,
        dead_load_lbs: float,
        material_properties: dict[str, float],
        n_segments: int = 10,
    ) -> Data:
        """Create PyTorch Geometric Data object from pole structure.
        
        Discretizes the pole into segments and creates a graph where:
        - Nodes represent connection points along the pole
        - Edges represent structural members (pole segments)
        - Node features include position, loads, boundary conditions
        - Edge features include member properties (area, I, material)
        
        Args:
            pole_height_ft: Pole height above grade
            pole_diameter_in: Pole outside diameter
            sign_height_ft: Sign face height
            sign_width_ft: Sign face width
            wind_force_lbs: Applied wind force
            dead_load_lbs: Dead load (sign weight)
            material_properties: Dict with E, fy, area, Ix, Iy
            n_segments: Number of segments to discretize pole
            
        Returns:
            PyTorch Geometric Data object ready for GNN processing
        """
        logger.info("graph.create.start",
                   height=pole_height_ft,
                   segments=n_segments)
        
        # Create nodes along pole height
        nodes = []
        node_positions = []
        
        # Base node (fixed boundary condition)
        nodes.append({
            "position": [0, 0, 0],
            "boundary": [1, 1, 1],  # Fixed in x, y, z
            "load": [0, 0, 0],  # No direct load at base
            "material_fy": material_properties.get("fy", 46.0),
        })
        node_positions.append([0, 0, 0])
        
        # Intermediate nodes
        for i in range(1, n_segments):
            z = (i / n_segments) * pole_height_ft
            
            nodes.append({
                "position": [0, 0, z],
                "boundary": [0, 0, 0],  # Free to move
                "load": [0, 0, 0],  # No load at intermediate points
                "material_fy": material_properties.get("fy", 46.0),
            })
            node_positions.append([0, 0, z])
        
        # Top node (where sign attaches)
        sign_centroid_height = pole_height_ft + sign_height_ft / 2
        
        nodes.append({
            "position": [0, 0, pole_height_ft],
            "boundary": [0, 0, 0],  # Free
            "load": [wind_force_lbs, 0, -dead_load_lbs],  # Wind + dead load
            "material_fy": material_properties.get("fy", 46.0),
        })
        node_positions.append([0, 0, pole_height_ft])
        
        # Build node feature matrix
        # Features: [x, y, z, boundary_x, boundary_y, boundary_z, load_x, load_y, load_z, material_fy]
        node_features = []
        for node in nodes:
            features = (
                node["position"] +
                node["boundary"] +
                node["load"] +
                [node["material_fy"]]
            )
            node_features.append(features)
        
        x = torch.tensor(node_features, dtype=torch.float32)
        
        # Create edges (pole segments connecting consecutive nodes)
        edge_index = []
        edge_attr = []
        
        for i in range(len(nodes) - 1):
            # Bidirectional edges
            edge_index.append([i, i + 1])
            edge_index.append([i + 1, i])
            
            # Edge features: [area, Ix, Iy, length, E_modulus]
            segment_length = nodes[i + 1]["position"][2] - nodes[i]["position"][2]
            
            edge_features = [
                material_properties.get("area", 10.0),
                material_properties.get("Ix", 50.0),
                material_properties.get("Iy", 50.0),
                segment_length,
                material_properties.get("E", 29000.0),  # ksi
            ]
            
            edge_attr.append(edge_features)
            edge_attr.append(edge_features)  # Same for both directions
        
        edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
        edge_attr = torch.tensor(edge_attr, dtype=torch.float32)
        
        # Create Data object
        graph = Data(
            x=x,
            edge_index=edge_index,
            edge_attr=edge_attr,
            num_nodes=len(nodes),
        )
        
        # Store metadata
        graph.pole_height_ft = pole_height_ft
        graph.n_segments = n_segments
        graph.wind_force_lbs = wind_force_lbs
        
        logger.info("graph.create.complete",
                   nodes=len(nodes),
                   edges=edge_index.shape[1])
        
        return graph
    
    @staticmethod
    def add_target_values(
        graph: Data,
        stress_values: list[float],
        deflection_values: list[float]
    ) -> Data:
        """Add target values to graph for supervised training.
        
        Args:
            graph: PyG Data object
            stress_values: Stress at each node (psi)
            deflection_values: Deflection at each node (inches)
            
        Returns:
            Updated graph with target tensors
        """
        graph.y_stress = torch.tensor(stress_values, dtype=torch.float32)
        graph.y_deflection = torch.tensor(deflection_values, dtype=torch.float32)
        
        return graph
    
    @staticmethod
    def visualize_graph(graph: Data, output_path: Optional[Path] = None) -> None:
        """Visualize structure graph using networkx and matplotlib.
        
        Args:
            graph: PyG Data object
            output_path: Optional path to save visualization
        """
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
            from torch_geometric.utils import to_networkx
        except ImportError:
            logger.warning("graph.visualize.missing_deps", 
                          message="Install matplotlib and networkx for visualization")
            return
        
        # Convert to networkx
        G = to_networkx(graph, to_undirected=True)
        
        # Extract positions from node features (x, y, z coordinates)
        pos_3d = graph.x[:, :3].numpy()
        pos_2d = {i: (pos_3d[i, 0], pos_3d[i, 2]) for i in range(len(pos_3d))}  # x-z plane
        
        # Create figure
        plt.figure(figsize=(8, 12))
        
        # Draw graph
        nx.draw(
            G,
            pos=pos_2d,
            with_labels=True,
            node_color='lightblue',
            node_size=500,
            font_size=8,
            font_weight='bold',
            arrows=False,
            edge_color='gray',
            width=2,
        )
        
        plt.title("Structure Graph Representation")
        plt.xlabel("X (ft)")
        plt.ylabel("Z (ft)")
        plt.grid(True, alpha=0.3)
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info("graph.visualize.saved", path=str(output_path))
        else:
            plt.show()
        
        plt.close()


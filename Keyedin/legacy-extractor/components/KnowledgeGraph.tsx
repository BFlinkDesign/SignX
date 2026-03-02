import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { GraphNode } from '../types';
import clsx from 'clsx';

interface KnowledgeGraphProps {
  nodes: GraphNode[];
  className?: string;
}

export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({ nodes, className }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!svgRef.current || !wrapperRef.current || nodes.length === 0) return;

    const width = wrapperRef.current.clientWidth;
    const height = wrapperRef.current.clientHeight;

    // Clear previous
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current)
      .attr("viewBox", [0, 0, width, height]);

    // Clone nodes to prevent mutation of the constant props in StrictMode
    // D3 forceSimulation mutates the object by adding x, y, vx, vy
    const simulationNodes = nodes.map(d => ({ ...d }));

    // Links data
    const links: any[] = [];
    const nodesMap = new Map(simulationNodes.map(n => [n.id, n]));
    
    simulationNodes.forEach(node => {
      node.connections.forEach(targetId => {
        if (nodesMap.has(targetId)) {
          links.push({ source: node.id, target: targetId });
        }
      });
    });

    // Simulation
    const simulation = d3.forceSimulation(simulationNodes as any)
      .force("link", d3.forceLink(links).id((d: any) => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2));

    // Draw Lines
    const link = svg.append("g")
      .attr("stroke", "#334155") // Slate-700
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", 1.5);

    // Draw Nodes
    const node = svg.append("g")
      .selectAll("g")
      .data(simulationNodes)
      .join("g")
      .call(d3.drag<any, any>()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // Node Circles
    node.append("circle")
      .attr("r", 8)
      .attr("fill", (d: any) => {
        if (d.type === 'root') return '#ef4444'; // Red
        if (d.status === 'scanning') return '#f59e0b'; // Amber
        if (d.type === 'dashboard') return '#3b82f6'; // Blue
        return '#22c55e'; // Green
      })
      .attr("stroke", "#0f172a")
      .attr("stroke-width", 2);
      
    // Node Pulse for active/scanning
    node.filter((d: any) => d.status === 'scanning')
      .append("circle")
      .attr("r", 12)
      .attr("fill", "none")
      .attr("stroke", "#f59e0b")
      .attr("stroke-opacity", 0.5)
      .append("animate")
      .attr("attributeName", "r")
      .attr("from", "8")
      .attr("to", "20")
      .attr("dur", "1.5s")
      .attr("repeatCount", "indefinite");
      
    node.filter((d: any) => d.status === 'scanning')
      .select("animate")
      .clone(true)
      .attr("attributeName", "opacity")
      .attr("from", "0.8")
      .attr("to", "0");

    // Labels
    node.append("text")
      .attr("x", 12)
      .attr("y", 4)
      .text((d: any) => d.label)
      .attr("fill", "#94a3b8") // Slate-400
      .attr("font-size", "10px")
      .attr("font-family", "monospace");

    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node
        .attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [nodes]);

  return (
    <div ref={wrapperRef} className={clsx("w-full h-full relative", className)}>
      <svg ref={svgRef} className="w-full h-full block"></svg>
      <div className="absolute top-4 right-4 bg-slate-900/80 backdrop-blur p-3 rounded-lg border border-slate-800 text-[10px] text-slate-400">
        <div className="flex items-center mb-1"><div className="w-2 h-2 rounded-full bg-red-500 mr-2"></div>Root Gate</div>
        <div className="flex items-center mb-1"><div className="w-2 h-2 rounded-full bg-blue-500 mr-2"></div>Dashboard</div>
        <div className="flex items-center mb-1"><div className="w-2 h-2 rounded-full bg-green-500 mr-2"></div>Mapped Node</div>
        <div className="flex items-center"><div className="w-2 h-2 rounded-full bg-amber-500 mr-2"></div>Active Scan</div>
      </div>
    </div>
  );
};
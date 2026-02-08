"use client";

import React, { useCallback } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  BackgroundVariant,
} from '@xyflow/react';

import '@xyflow/react/dist/style.css';
import { Hammer, Calculator, FileText, Truck } from 'lucide-react';

const initialNodes = [
  {
    id: '1',
    position: { x: 250, y: 0 },
    data: { label: 'Project: Starbucks Austin' },
    style: { background: '#fff', border: '1px solid #777', padding: 10, borderRadius: 5, fontWeight: 'bold' }
  },
  {
    id: '2',
    position: { x: 100, y: 150 },
    data: { label: <div className="flex items-center gap-2"><Calculator size={16} /> Engineering (APEX)</div> },
    style: { background: '#e0f2fe', border: '1px solid #0ea5e9', padding: 10, borderRadius: 5 }
  },
  {
    id: '3',
    position: { x: 400, y: 150 },
    data: { label: <div className="flex items-center gap-2"><FileText size={16} /> Costing</div> },
    style: { background: '#dcfce7', border: '1px solid #22c55e', padding: 10, borderRadius: 5 }
  },
  {
    id: '4',
    position: { x: 250, y: 300 },
    data: { label: <div className="flex items-center gap-2"><Hammer size={16} /> Fabrication</div> },
    style: { background: '#fef9c3', border: '1px solid #eab308', padding: 10, borderRadius: 5 }
  },
  {
    id: '5',
    position: { x: 250, y: 450 },
    data: { label: <div className="flex items-center gap-2"><Truck size={16} /> Installation</div> },
    style: { background: '#f3e8ff', border: '1px solid #a855f7', padding: 10, borderRadius: 5 }
  },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true },
  { id: 'e1-3', source: '1', target: '3', animated: true },
  { id: 'e2-4', source: '2', target: '4' },
  { id: 'e3-4', source: '3', target: '4' },
  { id: 'e4-5', source: '4', target: '5', animated: true },
];

export default function App() {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
      >
        <Controls />
        <MiniMap />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />

        <div className="absolute top-4 left-4 z-10 bg-white p-4 rounded-lg shadow-lg border">
          <h1 className="text-xl font-bold mb-2">SignX Studio</h1>
          <p className="text-sm text-gray-600">The &quot;Lego Builder&quot; for Signage</p>
          <div className="mt-4 text-xs text-gray-500">
            Drag nodes to reorganize workflow.<br />
            Connect blocks to define dependencies.
          </div>
        </div>
      </ReactFlow>
    </div>
  );
}

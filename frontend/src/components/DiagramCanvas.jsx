import { useCallback, useState, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import NodeTooltip from './NodeTooltip';
import CustomNode from './CustomNode';

const nodeTypes = {
  custom: CustomNode,
};

export default function DiagramCanvas({ diagram, onNodeClick }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  // Update nodes and edges when diagram changes
  useEffect(() => {
    if (!diagram) return;

    console.log('DiagramCanvas received diagram:', diagram);
    console.log('Number of nodes:', diagram.nodes?.length);
    console.log('Number of edges:', diagram.edges?.length);

    const flowNodes = diagram.nodes.map((node) => ({
      id: node.id,
      type: 'custom',
      position: node.position,
      data: {
        label: node.label,
        type: node.type,
        description: node.description,
        inputs: node.inputs,
        outputs: node.outputs,
        metadata: node.metadata,
      },
    }));

    const flowEdges = diagram.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      animated: edge.type === 'animated',
      style: { stroke: '#888' },
    }));

    console.log('Setting flowNodes:', flowNodes);
    console.log('Setting flowEdges:', flowEdges);

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [diagram, setNodes, setEdges]);

  const handleNodeMouseEnter = useCallback((event, node) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setTooltipPosition({
      x: rect.right + 10,
      y: rect.top,
    });
    setHoveredNode(node);
  }, []);

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredNode(null);
  }, []);

  const handleNodeClick = useCallback((event, node) => {
    onNodeClick(node);
  }, [onNodeClick]);

  if (!diagram) {
    return (
      <div className="diagram-canvas-empty">
        <p>Enter a system description to generate a diagram</p>
      </div>
    );
  }

  return (
    <div className="diagram-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onNodeMouseEnter={handleNodeMouseEnter}
        onNodeMouseLeave={handleNodeMouseLeave}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>

      {hoveredNode && (
        <div
          className="tooltip-container"
          style={{
            position: 'fixed',
            left: `${tooltipPosition.x}px`,
            top: `${tooltipPosition.y}px`,
          }}
        >
          <NodeTooltip node={hoveredNode} />
        </div>
      )}
    </div>
  );
}

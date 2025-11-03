import { useCallback, useState, useEffect, useRef } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import NodeTooltip from './NodeTooltip';
import CustomNode from './CustomNode';
import { getLayoutedElements } from '../utils/layout';

const nodeTypes = {
  custom: CustomNode,
};

function DiagramCanvasInner({ diagram, loading, onNodeClick, onDeleteNode, onAddEdge, onDeleteEdge, onReactFlowInit, onUpdateNode }) {
  const reactFlowInstance = useReactFlow();

  // Pass the React Flow instance to parent
  useEffect(() => {
    if (onReactFlowInit && reactFlowInstance) {
      onReactFlowInit(reactFlowInstance);
    }
  }, [reactFlowInstance, onReactFlowInit]);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [contextMenu, setContextMenu] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const isTooltipHoveredRef = useRef(false);
  const hideTooltipTimeoutRef = useRef(null);

  // Update nodes and edges when diagram changes
  useEffect(() => {
    if (!diagram) return;

    console.log('DiagramCanvas received diagram:', diagram);
    console.log('Number of nodes:', diagram.nodes?.length);
    console.log('Number of edges:', diagram.edges?.length);

    const flowNodes = diagram.nodes.map((node) => ({
      id: node.id,
      type: 'custom',
      position: node.position || { x: 0, y: 0 }, // Fallback position
      data: {
        label: node.label,
        type: node.type,
        description: node.description,
        inputs: node.inputs,
        outputs: node.outputs,
        metadata: node.metadata,
        onDelete: onDeleteNode,
      },
    }));

    const flowEdges = diagram.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      animated: edge.type === 'animated',
      style: {
        stroke: selectedEdge === edge.id ? '#667eea' : '#888',
        strokeWidth: selectedEdge === edge.id ? 3 : 2,
      },
      markerEnd: {
        type: 'arrowclosed',
        color: selectedEdge === edge.id ? '#667eea' : '#888',
      },
    }));

    // Apply auto-layout
    const layoutedNodes = getLayoutedElements(flowNodes, flowEdges, 'TB');

    console.log('Setting layoutedNodes:', layoutedNodes);
    console.log('Setting flowEdges:', flowEdges);

    setNodes(layoutedNodes);
    setEdges(flowEdges);
  }, [diagram, setNodes, setEdges, onDeleteNode, selectedEdge]);

  const handleNodeMouseEnter = useCallback((event, node) => {
    // Clear any pending hide timeout
    if (hideTooltipTimeoutRef.current) {
      clearTimeout(hideTooltipTimeoutRef.current);
      hideTooltipTimeoutRef.current = null;
    }

    const rect = event.currentTarget.getBoundingClientRect();
    setTooltipPosition({
      x: rect.right + 10,
      y: rect.top,
    });
    setHoveredNode(node);
    isTooltipHoveredRef.current = false;
  }, []);

  const handleNodeMouseLeave = useCallback(() => {
    // Give user time to move mouse to tooltip
    hideTooltipTimeoutRef.current = setTimeout(() => {
      // Check if mouse is now on tooltip using ref (not stale closure)
      if (!isTooltipHoveredRef.current) {
        setHoveredNode(null);
      }
    }, 200);
  }, []);

  const handleTooltipMouseEnter = useCallback(() => {
    // Clear any pending hide timeout
    if (hideTooltipTimeoutRef.current) {
      clearTimeout(hideTooltipTimeoutRef.current);
      hideTooltipTimeoutRef.current = null;
    }
    isTooltipHoveredRef.current = true;
  }, []);

  const handleTooltipMouseLeave = useCallback(() => {
    isTooltipHoveredRef.current = false;
    setHoveredNode(null);
  }, []);

  const handleNodeClick = useCallback((event, node) => {
    onNodeClick(node);
  }, [onNodeClick]);

  const handleNodeContextMenu = useCallback((event, node) => {
    event.preventDefault();
    setContextMenu({
      nodeId: node.id,
      x: event.clientX,
      y: event.clientY,
    });
  }, []);

  const handleDeleteNode = useCallback(() => {
    if (contextMenu?.nodeId && onDeleteNode) {
      onDeleteNode(contextMenu.nodeId);
      setContextMenu(null);
    }
  }, [contextMenu, onDeleteNode]);

  const handleDeleteEdgeFromMenu = useCallback(() => {
    if (contextMenu?.edgeId && onDeleteEdge) {
      onDeleteEdge(contextMenu.edgeId);
      setContextMenu(null);
    }
  }, [contextMenu, onDeleteEdge]);

  const handlePaneClick = useCallback(() => {
    setContextMenu(null);
    setSelectedEdge(null);
  }, []);

  const handleEdgeClick = useCallback((event, edge) => {
    event.stopPropagation();
    setSelectedEdge(edge.id);
  }, []);

  const handleEdgeContextMenu = useCallback((event, edge) => {
    event.preventDefault();
    setContextMenu({
      edgeId: edge.id,
      x: event.clientX,
      y: event.clientY,
    });
  }, []);

  const handleConnect = useCallback((connection) => {
    if (onAddEdge) {
      // Generate unique edge ID
      const edgeId = `edge-${connection.source}-${connection.target}-${Date.now()}`;

      const newEdge = {
        id: edgeId,
        source: connection.source,
        target: connection.target,
        label: null,
        type: 'default',
      };

      onAddEdge(newEdge);
    }
  }, [onAddEdge]);

  const handleEdgesDelete = useCallback((edgesToDelete) => {
    if (onDeleteEdge) {
      edgesToDelete.forEach(edge => {
        onDeleteEdge(edge.id);
      });
    }
  }, [onDeleteEdge]);

  const handleEdgeUpdate = useCallback((oldEdge, newConnection) => {
    // When user drags edge to reconnect, delete old and create new
    if (onDeleteEdge && onAddEdge) {
      // Delete old edge
      onDeleteEdge(oldEdge.id);

      // Create new edge with updated connection
      const newEdge = {
        id: `edge-${newConnection.source}-${newConnection.target}-${Date.now()}`,
        source: newConnection.source,
        target: newConnection.target,
        label: oldEdge.label || null,
        type: 'default',
      };

      onAddEdge(newEdge);
    }
  }, [onDeleteEdge, onAddEdge]);

  if (!diagram && !loading) {
    return (
      <div className="diagram-canvas-empty">
        <p>Enter a system description to generate a diagram</p>
      </div>
    );
  }

  if (!diagram && loading) {
    return null; // Loading animation is shown by InputPanel
  }

  return (
    <div className="diagram-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onEdgesDelete={handleEdgesDelete}
        onConnect={handleConnect}
        onEdgeUpdate={handleEdgeUpdate}
        onEdgeClick={handleEdgeClick}
        onEdgeContextMenu={handleEdgeContextMenu}
        onNodeClick={handleNodeClick}
        onNodeContextMenu={handleNodeContextMenu}
        onNodeMouseEnter={handleNodeMouseEnter}
        onNodeMouseLeave={handleNodeMouseLeave}
        onPaneClick={handlePaneClick}
        nodeTypes={nodeTypes}
        fitView
        edgesReconnectable={true}
        edgesUpdatable={true}
        edgesFocusable={true}
      >
        <Background />
        <Controls />
      </ReactFlow>

      {hoveredNode && (
        <div
          className="tooltip-container"
          style={{
            position: 'fixed',
            left: `${tooltipPosition.x}px`,
            top: `${tooltipPosition.y}px`,
          }}
          onMouseEnter={handleTooltipMouseEnter}
          onMouseLeave={handleTooltipMouseLeave}
        >
          <NodeTooltip
            node={hoveredNode}
            onSave={onUpdateNode}
            edges={edges}
            nodes={nodes}
          />
        </div>
      )}

      {contextMenu && (
        <div
          className="context-menu"
          style={{
            position: 'fixed',
            left: `${contextMenu.x}px`,
            top: `${contextMenu.y}px`,
          }}
        >
          {contextMenu.nodeId && (
            <button onClick={handleDeleteNode}>Delete Node</button>
          )}
          {contextMenu.edgeId && (
            <button onClick={handleDeleteEdgeFromMenu}>Delete Connection</button>
          )}
        </div>
      )}
    </div>
  );
}

// Wrapper component with ReactFlowProvider
export default function DiagramCanvas(props) {
  return (
    <ReactFlowProvider>
      <DiagramCanvasInner {...props} />
    </ReactFlowProvider>
  );
}

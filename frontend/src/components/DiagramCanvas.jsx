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
import NodePalette from './NodePalette';
import { getLayoutedElements } from '../utils/layout';

const nodeTypes = {
  custom: CustomNode,
};

function DiagramCanvasInner({ diagram, loading, onNodeClick, onDeleteNode, onAddEdge, onDeleteEdge, onReactFlowInit, onUpdateNode, onOpenNodePalette, onLayoutReady, onExportPng, designDocOpen, designDocWidth, chatPanelOpen, chatPanelWidth }) {
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
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const isTooltipHoveredRef = useRef(false);
  const hideTooltipTimeoutRef = useRef(null);

  // Function to apply layout to current nodes/edges
  const applyLayout = useCallback(() => {
    setNodes((currentNodes) => {
      setEdges((currentEdges) => {
        const layoutedNodes = getLayoutedElements(currentNodes, currentEdges, 'TB');

        // Use fitView to center the diagram after layout
        setTimeout(() => {
          reactFlowInstance?.fitView({ padding: 0.2, duration: 400 });
        }, 10);

        return currentEdges;
      });
      return getLayoutedElements(currentNodes, edges, 'TB');
    });
  }, [setNodes, setEdges, edges, reactFlowInstance]);

  // Expose applyLayout to parent component
  useEffect(() => {
    if (onLayoutReady) {
      onLayoutReady(applyLayout);
    }
  }, [onLayoutReady, applyLayout]);

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

  // Re-layout when panels open/close or resize (debounced)
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (nodes.length > 0 && reactFlowInstance) {
        reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
      }
    }, 100);

    return () => clearTimeout(timeoutId);
  }, [designDocOpen, chatPanelOpen, designDocWidth, chatPanelWidth, reactFlowInstance, nodes.length]);

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

  const handleSelectNodeType = useCallback((nodeType) => {
    // Keep palette open - only close when user clicks X or backdrop
    if (onOpenNodePalette) {
      onOpenNodePalette(nodeType);
    }
  }, [onOpenNodePalette]);

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
        minZoom={0.1}
        maxZoom={2}
        edgesReconnectable={true}
        edgesUpdatable={true}
        edgesFocusable={true}
      >
        <Background />
        <Controls />
      </ReactFlow>

      {/* Floating action buttons */}
      <div className="floating-buttons">
        <button
          className="floating-edit-button"
          onClick={() => setIsPaletteOpen(true)}
          title="Add component"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
        </button>
        <button
          className="floating-layout-button"
          onClick={applyLayout}
          title="Re-organize layout"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="21 16 21 21 16 21"></polyline>
            <path d="M14 8l-2-2-2 2"></path>
            <path d="M12 6v9"></path>
            <polyline points="3 8 3 3 8 3"></polyline>
          </svg>
        </button>
        <button
          className="floating-camera-button"
          onClick={onExportPng}
          title="Export as PNG"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
            <circle cx="12" cy="13" r="4"></circle>
          </svg>
        </button>
      </div>

      {/* Node palette */}
      <NodePalette
        isOpen={isPaletteOpen}
        onClose={() => setIsPaletteOpen(false)}
        onSelectType={handleSelectNodeType}
        designDocOpen={designDocOpen}
        designDocWidth={designDocWidth}
        chatPanelOpen={chatPanelOpen}
        chatPanelWidth={chatPanelWidth}
      />

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

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

// Color map for node types (matches index.css variables)
const COLOR_MAP = {
  database: '#4A90E2',
  cache: '#F5A623',
  server: '#7ED321',
  api: '#BD10E0',
  loadbalancer: '#50E3C2',
  queue: '#D0021B',
  cdn: '#9013FE',
  gateway: '#417505',
  storage: '#B8E986',
  service: '#8B572A',
  group: '#ffffff', // Default for group (will be overridden by blending)
};

// Helper function to blend multiple hex colors by averaging RGB values
function blendColors(hexColors) {
  if (!hexColors || hexColors.length === 0) {
    return COLOR_MAP.group; // Fallback
  }

  if (hexColors.length === 1) {
    return hexColors[0]; // Single color, no blending needed
  }

  // Convert hex to RGB
  const rgbs = hexColors.map(hex => {
    const clean = hex.replace('#', '');
    const r = parseInt(clean.slice(0, 2), 16);
    const g = parseInt(clean.slice(2, 4), 16);
    const b = parseInt(clean.slice(4, 6), 16);
    return [r, g, b];
  });

  // Average the RGB values
  const avgR = Math.round(rgbs.reduce((sum, rgb) => sum + rgb[0], 0) / rgbs.length);
  const avgG = Math.round(rgbs.reduce((sum, rgb) => sum + rgb[1], 0) / rgbs.length);
  const avgB = Math.round(rgbs.reduce((sum, rgb) => sum + rgb[2], 0) / rgbs.length);

  // Adjust brightness if result is too dark (ensure readability)
  const brightness = (avgR * 299 + avgG * 587 + avgB * 114) / 1000;
  let finalR = avgR, finalG = avgG, finalB = avgB;

  if (brightness < 80) {
    // Too dark, lighten it
    const factor = 80 / brightness;
    finalR = Math.min(255, Math.round(avgR * factor));
    finalG = Math.min(255, Math.round(avgG * factor));
    finalB = Math.min(255, Math.round(avgB * factor));
  }

  // Convert back to hex
  return `#${finalR.toString(16).padStart(2, '0')}${finalG.toString(16).padStart(2, '0')}${finalB.toString(16).padStart(2, '0')}`;
}

const EXAMPLE_PROMPTS = [
  {
    title: "Video Streaming Platform",
    prompt: "Build a scalable video streaming platform with CDN, transcoding, and personalized recommendations",
    icon: "🎬"
  },
  {
    title: "E-Commerce System",
    prompt: "Design a microservices-based e-commerce platform with payment processing, inventory management, and order tracking",
    icon: "🛒"
  },
  {
    title: "Real-Time Chat App",
    prompt: "Create a real-time chat application with WebSocket connections, message queues, and presence detection",
    icon: "💬"
  },
  {
    title: "Data Analytics Pipeline",
    prompt: "Build a data analytics pipeline with stream processing, data warehousing, and real-time dashboards",
    icon: "📊"
  }
];

function DiagramCanvasInner({ diagram, loading, onNodeClick, onDeleteNode, onAddEdge, onDeleteEdge, onReactFlowInit, onUpdateNode, onOpenNodePalette, onLayoutReady, onExportPng, onExampleClick, designDocOpen, designDocWidth, chatPanelOpen, chatPanelWidth, layoutDirection = 'TB', onLayoutDirectionChange, onMergeNodes, onUngroupNodes, onToggleCollapse, onRegenerateDescription, mergingNodes = false, onToggleAllGroups, hasExpandedGroups }) {
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

  // Drag-to-merge state
  const [draggedNode, setDraggedNode] = useState(null);
  const [dropTarget, setDropTarget] = useState(null);
  const dropTargetTimeoutRef = useRef(null);
  const isDraggingRef = useRef(false);

  // Function to apply layout to current nodes/edges
  const applyLayout = useCallback(() => {
    setNodes((currentNodes) => {
      setEdges((currentEdges) => {
        const layoutedNodes = getLayoutedElements(currentNodes, currentEdges, layoutDirection);

        // Use fitView to center the diagram after layout
        setTimeout(() => {
          reactFlowInstance?.fitView({ padding: 0.2, duration: 400 });
        }, 10);

        return currentEdges;
      });
      return getLayoutedElements(currentNodes, edges, layoutDirection);
    });
  }, [setNodes, setEdges, edges, reactFlowInstance, layoutDirection]);

  // Expose applyLayout to parent component
  useEffect(() => {
    if (onLayoutReady) {
      onLayoutReady(applyLayout);
    }
  }, [onLayoutReady, applyLayout]);

  // Separate effect to update drop target highlighting during drag (without recalculating layout)
  useEffect(() => {
    if (!isDraggingRef.current || !dropTarget) return;

    // Only update the node data to show drop target, keep positions unchanged
    setNodes((currentNodes) =>
      currentNodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          isDropTarget: dropTarget?.id === node.id,
        },
      }))
    );
  }, [dropTarget, setNodes]);

  // Update nodes and edges when diagram changes
  useEffect(() => {
    if (!diagram) return;

    // Skip updates while dragging to prevent node position reset
    if (isDraggingRef.current) return;

    console.log('DiagramCanvas received diagram:', diagram);
    console.log('Number of nodes:', diagram.nodes?.length);
    console.log('Number of edges:', diagram.edges?.length);

    // First, create all flow nodes
    const allFlowNodes = diagram.nodes.map((node) => {
      // Calculate blended color for mixed-type groups
      let blendedColor = null;
      if (node.is_group && node.type === 'group' && node.metadata?.child_types) {
        // Get unique child types
        const uniqueTypes = [...new Set(node.metadata.child_types)];
        // Map to colors
        const colors = uniqueTypes.map(type => COLOR_MAP[type] || COLOR_MAP.group);
        // Blend them
        blendedColor = blendColors(colors);
      }

      return {
        id: node.id,
        type: 'custom',
        position: node.position || { x: 0, y: 0 },
        data: {
          label: node.label,
          type: node.type,
          description: node.description,
          inputs: node.inputs,
          outputs: node.outputs,
          metadata: node.metadata,
          onDelete: onDeleteNode,
          onToggleCollapse: onToggleCollapse,
          isDropTarget: dropTarget?.id === node.id,
          is_group: node.is_group,
          is_collapsed: node.is_collapsed,
          child_ids: node.child_ids,
          parent_id: node.parent_id,
          blendedColor: blendedColor, // Pass calculated color to CustomNode
        },
        nodeData: node, // Keep reference to original node data
      };
    });

    // Filter visible nodes based on collapsed groups
    const visibleNodes = allFlowNodes.filter(node => {
      // Hide expanded group nodes (only show collapsed groups)
      if (node.nodeData.is_group && !node.nodeData.is_collapsed) {
        return false;
      }

      const parentId = node.nodeData.parent_id;
      if (!parentId) return true; // No parent, always visible

      const parent = diagram.nodes.find(n => n.id === parentId);
      if (!parent) return true; // Parent not found, show node

      // Hide if parent is collapsed
      return !parent.is_collapsed;
    });

    // Process edges: redirect through collapsed groups
    let flowEdges = diagram.edges.map((edge) => {
      let source = edge.source;
      let target = edge.target;

      // Check if source node is inside a collapsed group
      const sourceNode = diagram.nodes.find(n => n.id === source);
      if (sourceNode?.parent_id) {
        const sourceParent = diagram.nodes.find(n => n.id === sourceNode.parent_id);
        if (sourceParent?.is_collapsed) {
          source = sourceParent.id;
        }
      }

      // Check if target node is inside a collapsed group
      const targetNode = diagram.nodes.find(n => n.id === target);
      if (targetNode?.parent_id) {
        const targetParent = diagram.nodes.find(n => n.id === targetNode.parent_id);
        if (targetParent?.is_collapsed) {
          target = targetParent.id;
        }
      }

      return {
        id: edge.id,
        source: source,
        target: target,
        label: edge.label,
        animated: edge.type === 'animated',
        originalSource: edge.source,
        originalTarget: edge.target,
      };
    });

    // Filter out self-loops (same source and target after redirection)
    flowEdges = flowEdges.filter(edge => edge.source !== edge.target);

    // Deduplicate edges: merge multiple edges between same nodes
    const edgeMap = new Map();
    flowEdges.forEach(edge => {
      const key = `${edge.source}-${edge.target}`;
      if (edgeMap.has(key)) {
        const existing = edgeMap.get(key);
        // Merge labels
        if (edge.label && !existing.labels.includes(edge.label)) {
          existing.labels.push(edge.label);
        }
      } else {
        edgeMap.set(key, {
          ...edge,
          labels: edge.label ? [edge.label] : [],
        });
      }
    });

    // Convert back to array with merged labels
    const deduplicatedEdges = Array.from(edgeMap.values()).map(edge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.labels.length > 0 ? edge.labels.join(', ') : null,
      animated: edge.animated,
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
    const layoutedNodes = getLayoutedElements(visibleNodes, deduplicatedEdges, layoutDirection);

    console.log('Setting layoutedNodes:', layoutedNodes);
    console.log('Setting deduplicatedEdges:', deduplicatedEdges);

    setNodes(layoutedNodes);
    setEdges(deduplicatedEdges);
  }, [diagram, setNodes, setEdges, onDeleteNode, onToggleCollapse, selectedEdge, layoutDirection, dropTarget]);

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

  const handleUngroupNode = useCallback(() => {
    if (contextMenu?.nodeId && onUngroupNodes) {
      onUngroupNodes(contextMenu.nodeId);
      setContextMenu(null);
    }
  }, [contextMenu, onUngroupNodes]);

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

  // Drag-to-merge handlers
  const handleNodeDragStart = useCallback((event, node) => {
    isDraggingRef.current = true;
    setDraggedNode(node);
    setDropTarget(null);
  }, []);

  const handleNodeDrag = useCallback((event, node) => {
    if (!node) return;

    // Clear any pending timeout
    if (dropTargetTimeoutRef.current) {
      clearTimeout(dropTargetTimeoutRef.current);
    }

    // Get the dragged node's element
    const draggedElement = document.querySelector(`[data-id="${node.id}"]`);
    if (!draggedElement) return;

    const draggedBounds = draggedElement.getBoundingClientRect();

    // Find overlapping node with the MOST overlap
    let bestMatch = null;
    let maxOverlap = 0;

    nodes.forEach(n => {
      if (n.id === node.id) return; // Don't collide with self
      if (n.data.type === 'group' && diagram?.nodes?.find(dn => dn.id === n.id)?.parent_id) {
        // Don't merge with groups that are children of other groups
        return;
      }

      const nodeElement = document.querySelector(`[data-id="${n.id}"]`);
      if (!nodeElement) return;

      const nodeBounds = nodeElement.getBoundingClientRect();

      // Check for actual overlap
      const horizontalOverlap = draggedBounds.left < nodeBounds.right && draggedBounds.right > nodeBounds.left;
      const verticalOverlap = draggedBounds.top < nodeBounds.bottom && draggedBounds.bottom > nodeBounds.top;

      if (horizontalOverlap && verticalOverlap) {
        // Calculate overlap area
        const xOverlap = Math.max(0, Math.min(draggedBounds.right, nodeBounds.right) - Math.max(draggedBounds.left, nodeBounds.left));
        const yOverlap = Math.max(0, Math.min(draggedBounds.bottom, nodeBounds.bottom) - Math.max(draggedBounds.top, nodeBounds.top));
        const overlapArea = xOverlap * yOverlap;

        // Calculate percentage based on smaller node
        const draggedArea = (draggedBounds.right - draggedBounds.left) * (draggedBounds.bottom - draggedBounds.top);
        const targetArea = (nodeBounds.right - nodeBounds.left) * (nodeBounds.bottom - nodeBounds.top);
        const smallerArea = Math.min(draggedArea, targetArea);
        const overlapPercent = overlapArea / smallerArea;

        // Require 15% overlap to prevent accidental merges
        if (overlapPercent > 0.15 && overlapArea > maxOverlap) {
          maxOverlap = overlapArea;
          bestMatch = n;
        }
      }
    });

    // Debounce: only update after 50ms of no movement to reduce flickering
    dropTargetTimeoutRef.current = setTimeout(() => {
      setDropTarget(bestMatch);
    }, 50);
  }, [nodes, diagram]);

  const handleNodeDragStop = useCallback(async (event, node) => {
    isDraggingRef.current = false;

    if (dropTarget && onMergeNodes && node.id !== dropTarget.id) {
      // User dropped node onto another node - merge them
      await onMergeNodes(node.id, dropTarget.id);
    }

    setDraggedNode(null);
    setDropTarget(null);
  }, [dropTarget, onMergeNodes]);

  // Show empty state if no diagram or diagram has no nodes
  const hasNodes = diagram?.nodes?.length > 0;
  if (!hasNodes && !loading) {
    return (
      <div className="diagram-canvas-empty">
        <h2>Start Building Your System Design</h2>
        <p>Add components manually or describe your system in the chat</p>
        <div className="empty-state-actions">
          <button onClick={() => onOpenNodePalette && onOpenNodePalette()} className="primary-action">
            Add Component
          </button>
          <span className="action-separator">or</span>
          <span className="chat-hint">Use the chat to describe your system →</span>
        </div>

        {/* Example Prompts */}
        <div className="empty-state-examples">
          <p className="examples-label">Or try an example:</p>
          <div className="examples-grid">
            {EXAMPLE_PROMPTS.map((example, index) => (
              <button
                key={index}
                onClick={() => onExampleClick && onExampleClick(example.prompt)}
                className="example-card"
              >
                <span className="example-icon">{example.icon}</span>
                <span className="example-title">{example.title}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!diagram && loading) {
    return null; // Loading animation is shown by InputPanel
  }

  return (
    <div className="diagram-canvas" style={{ cursor: mergingNodes ? 'wait' : 'default' }}>
      {/* Merging toast notification */}
      {mergingNodes && (
        <div className="merge-loading-toast">
          <div className="merge-loading-content">
            <div className="merge-loading-spinner"></div>
            <span>AI analyzing group... (1-2s)</span>
          </div>
        </div>
      )}

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
        onNodeDragStart={handleNodeDragStart}
        onNodeDrag={handleNodeDrag}
        onNodeDragStop={handleNodeDragStop}
        onPaneClick={handlePaneClick}
        nodeTypes={nodeTypes}
        nodesDraggable={!mergingNodes}
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

      {/* Empty state message */}
      {nodes.length === 0 && (
        <div className="canvas-empty-state">
          <div className="empty-state-content">
            <h3>Start Building Your System Design</h3>
            <p>Add components manually or describe your system in the chat</p>
            <div className="empty-state-actions">
              <button
                className="empty-state-button primary"
                onClick={() => onOpenNodePalette && onOpenNodePalette()}
              >
                Add Component
              </button>
              <span className="empty-state-divider">or</span>
              <span className="empty-state-hint">Use the chat to describe your system →</span>
            </div>
          </div>
        </div>
      )}

      {/* Floating action buttons */}
      <div className="floating-buttons">
        <button
          className="floating-edit-button"
          onClick={() => onOpenNodePalette && onOpenNodePalette()}
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
          className="floating-direction-button"
          onClick={() => {
            const newDirection = layoutDirection === 'TB' ? 'LR' : 'TB';
            onLayoutDirectionChange && onLayoutDirectionChange(newDirection);
          }}
          title={`Switch to ${layoutDirection === 'TB' ? 'horizontal' : 'vertical'} layout`}
        >
          {layoutDirection === 'TB' ? (
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
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
              <line x1="10" y1="6.5" x2="14" y2="6.5"></line>
              <line x1="10" y1="17.5" x2="14" y2="17.5"></line>
            </svg>
          ) : (
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
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <line x1="6.5" y1="10" x2="6.5" y2="14"></line>
              <line x1="17.5" y1="10" x2="17.5" y2="14"></line>
            </svg>
          )}
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
        {/* Toggle expand/collapse all button - only show if diagram has groups */}
        {diagram?.nodes?.some(n => n.is_group) && (
          <button
            className="floating-toggle-groups-button"
            onClick={onToggleAllGroups}
            title={hasExpandedGroups ? "Collapse all groups" : "Expand all groups"}
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
              {hasExpandedGroups ? (
                <>
                  {/* Collapse icon - arrows pointing inward */}
                  <polyline points="4 14 10 14 10 20"></polyline>
                  <polyline points="20 10 14 10 14 4"></polyline>
                  <line x1="14" y1="10" x2="21" y2="3"></line>
                  <line x1="3" y1="21" x2="10" y2="14"></line>
                </>
              ) : (
                <>
                  {/* Expand icon - arrows pointing outward */}
                  <polyline points="15 3 21 3 21 9"></polyline>
                  <polyline points="9 21 3 21 3 15"></polyline>
                  <line x1="21" y1="3" x2="14" y2="10"></line>
                  <line x1="3" y1="21" x2="10" y2="14"></line>
                </>
              )}
            </svg>
          </button>
        )}
      </div>

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
            onRegenerateDescription={onRegenerateDescription}
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
          {contextMenu.nodeId && (() => {
            // Find the node to check if it's a group
            const node = diagram?.nodes?.find(n => n.id === contextMenu.nodeId);
            const isGroup = node?.is_group;

            return (
              <>
                {isGroup && (
                  <button onClick={handleUngroupNode}>Ungroup</button>
                )}
                <button onClick={handleDeleteNode}>Delete {isGroup ? 'Group' : 'Node'}</button>
              </>
            );
          })()}
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

import dagre from 'dagre';
import { MOBILE_BREAKPOINT } from '../constants/ui';

/**
 * Get responsive layout configuration based on viewport width
 * Phones (<=480px): Compact nodes and tight spacing
 * Tablets (<=768px): Medium nodes and spacing
 * Desktop (>768px): Full-size nodes and spacing
 */
const getResponsiveLayoutConfig = () => {
  const width = typeof window !== 'undefined' ? window.innerWidth : 1024;

  // Phone: 360-480px
  if (width <= 480) {
    return {
      nodeWidth: 140,
      nodeHeight: 70,
      nodesep: 25,
      ranksep: 50,
      marginx: 10,
      marginy: 10
    };
  }

  // Tablet: 481-768px
  if (width <= MOBILE_BREAKPOINT) {
    return {
      nodeWidth: 180,
      nodeHeight: 80,
      nodesep: 35,
      ranksep: 60,
      marginx: 20,
      marginy: 20
    };
  }

  // Desktop: >768px
  return {
    nodeWidth: 250,
    nodeHeight: 100,
    nodesep: 50,
    ranksep: 80,
    marginx: 30,
    marginy: 30
  };
};

/**
 * A node counts as "placed" only if the backend holds a real coordinate for it.
 * Node.position defaults to {x: 0, y: 0} server-side, so the origin means
 * "never positioned" rather than "positioned at the origin". A node genuinely
 * dragged to exactly (0, 0) just gets auto-placed once more.
 */
export const hasStoredPosition = (node) => {
  const position = node?.nodeData?.position;
  if (!position) return false;
  if (typeof position.x !== 'number' || typeof position.y !== 'number') return false;
  return position.x !== 0 || position.y !== 0;
};

/**
 * Auto-layout nodes using dagre (directed graph layout)
 * @param {Array} nodes - React Flow nodes
 * @param {Array} edges - React Flow edges
 * @param {string} direction - 'TB' (top-bottom) or 'LR' (left-right)
 * @param {Object} [options]
 * @param {boolean} [options.preserveStored=false] - Keep each node's saved
 *   position instead of the dagre result. Dagre still runs, so nodes with no
 *   saved position (newly added by chat, for example) land somewhere sensible
 *   instead of stacking at the origin.
 * @returns {Array} nodes with calculated positions
 */
export const getLayoutedElements = (nodes, edges, direction = 'TB', options = {}) => {
  const { preserveStored = false } = options;
  const config = getResponsiveLayoutConfig();
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  // Configure graph layout with responsive values
  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: config.nodesep,
    ranksep: config.ranksep,
    marginx: config.marginx,
    marginy: config.marginy
  });

  // Add nodes to dagre graph
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: config.nodeWidth, height: config.nodeHeight });
  });

  // Add edges to dagre graph
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // Calculate layout
  dagre.layout(dagreGraph);

  // Apply calculated positions to nodes
  const layoutedNodes = nodes.map((node) => {
    if (preserveStored && hasStoredPosition(node)) {
      return {
        ...node,
        position: { x: node.nodeData.position.x, y: node.nodeData.position.y },
      };
    }

    const nodeWithPosition = dagreGraph.node(node.id);

    return {
      ...node,
      position: {
        x: nodeWithPosition.x - config.nodeWidth / 2,
        y: nodeWithPosition.y - config.nodeHeight / 2,
      },
    };
  });

  return layoutedNodes;
};

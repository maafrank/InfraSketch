import { useCallback, useRef, useState } from 'react';

/**
 * Owns the node-hover tooltip state for DiagramCanvas: which node is
 * hovered, where the tooltip should sit, and the show/hide handlers
 * that coordinate the brief grace period for moving the cursor onto
 * the tooltip itself.
 *
 * Returns the props-shape DiagramCanvas already used (hoveredNode,
 * tooltipPosition, plus 4 handlers) so swapping the inline state for
 * the hook is mechanical at the call site.
 */
export function useNodeTooltip({ hideDelayMs = 200 } = {}) {
  const [hoveredNode, setHoveredNode] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  const isTooltipHoveredRef = useRef(false);
  const hideTooltipTimeoutRef = useRef(null);

  const handleNodeMouseEnter = useCallback((event, node) => {
    if (hideTooltipTimeoutRef.current) {
      clearTimeout(hideTooltipTimeoutRef.current);
      hideTooltipTimeoutRef.current = null;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    setTooltipPosition({ x: rect.right + 10, y: rect.top });
    setHoveredNode(node);
    isTooltipHoveredRef.current = false;
  }, []);

  const handleNodeMouseLeave = useCallback(() => {
    // Grace period so the user can move from node to tooltip without
    // the tooltip disappearing under the cursor.
    hideTooltipTimeoutRef.current = setTimeout(() => {
      if (!isTooltipHoveredRef.current) {
        setHoveredNode(null);
      }
    }, hideDelayMs);
  }, [hideDelayMs]);

  const handleTooltipMouseEnter = useCallback(() => {
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

  return {
    hoveredNode,
    tooltipPosition,
    handleNodeMouseEnter,
    handleNodeMouseLeave,
    handleTooltipMouseEnter,
    handleTooltipMouseLeave,
  };
}

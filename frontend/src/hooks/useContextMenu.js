import { useCallback, useState } from 'react';

/**
 * Owns the right-click context-menu state for DiagramCanvas (which node
 * or edge was right-clicked, screen position) and the handlers that
 * mutate it. Delete/ungroup actions delegate to caller-supplied
 * callbacks so the hook stays UI-only.
 *
 * The shape returned matches what DiagramCanvas already destructured
 * inline; replacing the inline state with this hook is mechanical.
 */
export function useContextMenu({ onDeleteNode, onUngroupNodes, onDeleteEdge } = {}) {
  const [contextMenu, setContextMenu] = useState(null);

  const openForNode = useCallback((event, node) => {
    event.preventDefault();
    setContextMenu({ nodeId: node.id, x: event.clientX, y: event.clientY });
  }, []);

  const openForEdge = useCallback((event, edge) => {
    event.preventDefault();
    setContextMenu({ edgeId: edge.id, x: event.clientX, y: event.clientY });
  }, []);

  const close = useCallback(() => setContextMenu(null), []);

  const deleteNode = useCallback(() => {
    if (contextMenu?.nodeId && onDeleteNode) {
      onDeleteNode(contextMenu.nodeId);
      setContextMenu(null);
    }
  }, [contextMenu, onDeleteNode]);

  const ungroupNode = useCallback(() => {
    if (contextMenu?.nodeId && onUngroupNodes) {
      onUngroupNodes(contextMenu.nodeId);
      setContextMenu(null);
    }
  }, [contextMenu, onUngroupNodes]);

  const deleteEdge = useCallback(() => {
    if (contextMenu?.edgeId && onDeleteEdge) {
      onDeleteEdge(contextMenu.edgeId);
      setContextMenu(null);
    }
  }, [contextMenu, onDeleteEdge]);

  return {
    contextMenu,
    openForNode,
    openForEdge,
    close,
    deleteNode,
    ungroupNode,
    deleteEdge,
  };
}

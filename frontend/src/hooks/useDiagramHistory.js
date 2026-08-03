import { useCallback, useRef, useState } from 'react';

// How many prior diagrams to keep. Each snapshot is a full Diagram, so this is
// bounded to keep memory flat on long sessions. 50 covers far more than anyone
// undoes in practice.
const MAX_HISTORY = 50;

/**
 * Undo/redo over whole-diagram snapshots.
 *
 * Every mutation endpoint returns a complete Diagram, so history is just a
 * stack of those. `record(previous)` is called with the pre-mutation diagram
 * before a mutation is applied; `undo()`/`redo()` return the diagram to restore
 * (or null when there is nothing to do) and the caller PUTs it back to the
 * server via replaceDiagram().
 *
 * Deliberately session-local: it resets on session load and is lost on reload.
 * Persisting it is a separate feature (version history), not undo.
 */
export function useDiagramHistory() {
  const undoStack = useRef([]);
  const redoStack = useRef([]);

  // Stacks live in refs so recording never triggers a render, but the buttons
  // need to re-render when availability changes, hence the mirrored state.
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);

  const syncFlags = useCallback(() => {
    setCanUndo(undoStack.current.length > 0);
    setCanRedo(redoStack.current.length > 0);
  }, []);

  /**
   * Push the pre-mutation diagram onto the undo stack.
   * Call this immediately before applying a mutation, not after.
   */
  const record = useCallback((previousDiagram) => {
    if (!previousDiagram) return;
    undoStack.current.push(previousDiagram);
    if (undoStack.current.length > MAX_HISTORY) {
      undoStack.current.shift();
    }
    // Any new edit invalidates the redo branch, matching every editor's behavior.
    redoStack.current = [];
    syncFlags();
  }, [syncFlags]);

  /**
   * Pop the last snapshot. `currentDiagram` is pushed onto the redo stack so
   * the step can be replayed. Returns the diagram to restore, or null.
   */
  const undo = useCallback((currentDiagram) => {
    if (undoStack.current.length === 0) return null;
    const previous = undoStack.current.pop();
    if (currentDiagram) redoStack.current.push(currentDiagram);
    syncFlags();
    return previous;
  }, [syncFlags]);

  /** Inverse of undo(). Returns the diagram to restore, or null. */
  const redo = useCallback((currentDiagram) => {
    if (redoStack.current.length === 0) return null;
    const next = redoStack.current.pop();
    if (currentDiagram) undoStack.current.push(currentDiagram);
    syncFlags();
    return next;
  }, [syncFlags]);

  /**
   * Drop all history. Called on session switch, new design, and session delete
   * so an undo can never restore a diagram belonging to a different session.
   */
  const reset = useCallback(() => {
    undoStack.current = [];
    redoStack.current = [];
    syncFlags();
  }, [syncFlags]);

  return { record, undo, redo, reset, canUndo, canRedo };
}

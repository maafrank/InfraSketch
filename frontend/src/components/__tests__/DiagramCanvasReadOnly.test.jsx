/**
 * The public share page renders DiagramCanvas with no interaction callbacks.
 * These tests pin that down: every parent callback must be optional, because a
 * missing one on the share page becomes a runtime crash for an anonymous
 * visitor who has no way to recover.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DiagramCanvas from '../DiagramCanvas';

vi.mock('reactflow', async () => {
  const actual = await vi.importActual('reactflow');
  return actual;
});

const diagram = {
  nodes: [
    { id: 'a', type: 'api', label: 'API', description: 'edge', position: { x: 0, y: 0 } },
    { id: 'b', type: 'database', label: 'DB', description: 'store', position: { x: 0, y: 100 } },
  ],
  edges: [{ id: 'e1', source: 'a', target: 'b' }],
  manual_layout: true,
};

describe('DiagramCanvas in read-only mode', () => {
  it('renders with no callbacks at all', () => {
    expect(() => render(<DiagramCanvas diagram={diagram} loading={false} />)).not.toThrow();
  });

  it('clicking a node does not throw when onNodeClick is absent', () => {
    const { container } = render(<DiagramCanvas diagram={diagram} loading={false} />);

    const nodes = container.querySelectorAll('.react-flow__node');
    expect(nodes.length).toBeGreaterThan(0);

    // Would throw "onNodeClick is not a function" without the guard.
    expect(() => fireEvent.click(nodes[0])).not.toThrow();
  });

  it('still calls onNodeClick when the parent provides one', () => {
    const onNodeClick = vi.fn();
    const { container } = render(
      <DiagramCanvas diagram={diagram} loading={false} onNodeClick={onNodeClick} />
    );

    fireEvent.click(container.querySelectorAll('.react-flow__node')[0]);

    expect(onNodeClick).toHaveBeenCalledTimes(1);
    expect(onNodeClick.mock.calls[0][0].id).toBe('a');
  });

  it('undo and redo buttons render disabled with no history', () => {
    render(<DiagramCanvas diagram={diagram} loading={false} />);

    expect(screen.getByLabelText('Undo')).toBeDisabled();
    expect(screen.getByLabelText('Redo')).toBeDisabled();
  });

  // Dispatched on body, not document: the handler is bound to document and
  // catches the bubbled event, and React Flow's own key handler expects an
  // Element target (document itself makes it throw inside its own code).
  it('pressing Cmd+Z with no handler does not throw', () => {
    render(<DiagramCanvas diagram={diagram} loading={false} />);

    expect(() =>
      fireEvent.keyDown(document.body, { key: 'z', metaKey: true })
    ).not.toThrow();
  });

  it('Cmd+Z reaches onUndo, and Cmd+Shift+Z reaches onRedo', () => {
    const onUndo = vi.fn();
    const onRedo = vi.fn();
    render(
      <DiagramCanvas diagram={diagram} loading={false} onUndo={onUndo} onRedo={onRedo} />
    );

    fireEvent.keyDown(document.body, { key: 'z', metaKey: true });
    expect(onUndo).toHaveBeenCalledTimes(1);
    expect(onRedo).not.toHaveBeenCalled();

    fireEvent.keyDown(document.body, { key: 'z', metaKey: true, shiftKey: true });
    expect(onRedo).toHaveBeenCalledTimes(1);
    expect(onUndo).toHaveBeenCalledTimes(1);
  });

  it('does not hijack Cmd+Z while the design doc editor has focus', () => {
    const onUndo = vi.fn();
    render(<DiagramCanvas diagram={diagram} loading={false} onUndo={onUndo} />);

    // TipTap renders a contenteditable and owns its own undo stack. Stealing
    // Cmd+Z there would silently revert the diagram mid-sentence.
    const editor = document.createElement('div');
    editor.setAttribute('contenteditable', 'true');
    document.body.appendChild(editor);

    fireEvent.keyDown(editor, { key: 'z', metaKey: true });
    expect(onUndo).not.toHaveBeenCalled();

    // TipTap's keydown often targets an element inside the editable region
    // rather than the editable root, so the guard must walk ancestors too.
    const inner = document.createElement('p');
    editor.appendChild(inner);
    fireEvent.keyDown(inner, { key: 'z', metaKey: true });
    expect(onUndo).not.toHaveBeenCalled();

    document.body.removeChild(editor);
  });

  it('does not hijack Cmd+Z while a text input has focus', () => {
    const onUndo = vi.fn();
    render(<DiagramCanvas diagram={diagram} loading={false} onUndo={onUndo} />);

    const input = document.createElement('input');
    document.body.appendChild(input);

    fireEvent.keyDown(input, { key: 'z', metaKey: true });

    expect(onUndo).not.toHaveBeenCalled();
    document.body.removeChild(input);
  });
});

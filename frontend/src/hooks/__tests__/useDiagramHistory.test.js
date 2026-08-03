import { describe, it, expect } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useDiagramHistory } from '../useDiagramHistory';

const diagram = (label) => ({ nodes: [{ id: 'n1', label }], edges: [] });

describe('useDiagramHistory', () => {
  it('starts with nothing to undo or redo', () => {
    const { result } = renderHook(() => useDiagramHistory());

    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
    expect(result.current.undo(diagram('current'))).toBeNull();
    expect(result.current.redo(diagram('current'))).toBeNull();
  });

  it('returns the recorded snapshot on undo', () => {
    const { result } = renderHook(() => useDiagramHistory());
    const before = diagram('before');

    act(() => result.current.record(before));
    expect(result.current.canUndo).toBe(true);

    let restored;
    act(() => { restored = result.current.undo(diagram('after')); });

    expect(restored).toBe(before);
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(true);
  });

  it('redo replays the undone step', () => {
    const { result } = renderHook(() => useDiagramHistory());
    const before = diagram('before');
    const after = diagram('after');

    act(() => result.current.record(before));
    act(() => { result.current.undo(after); });

    let redone;
    act(() => { redone = result.current.redo(before); });

    expect(redone).toBe(after);
    expect(result.current.canUndo).toBe(true);
    expect(result.current.canRedo).toBe(false);
  });

  it('unwinds multiple steps in reverse order', () => {
    const { result } = renderHook(() => useDiagramHistory());
    const v1 = diagram('v1');
    const v2 = diagram('v2');
    const v3 = diagram('v3');

    act(() => result.current.record(v1));
    act(() => result.current.record(v2));
    act(() => result.current.record(v3));

    let step;
    act(() => { step = result.current.undo(diagram('v4')); });
    expect(step).toBe(v3);
    act(() => { step = result.current.undo(v3); });
    expect(step).toBe(v2);
    act(() => { step = result.current.undo(v2); });
    expect(step).toBe(v1);
    expect(result.current.canUndo).toBe(false);
  });

  it('a new edit after an undo discards the redo branch', () => {
    const { result } = renderHook(() => useDiagramHistory());

    act(() => result.current.record(diagram('v1')));
    act(() => { result.current.undo(diagram('v2')); });
    expect(result.current.canRedo).toBe(true);

    act(() => result.current.record(diagram('v3')));

    expect(result.current.canRedo).toBe(false);
  });

  it('ignores a null snapshot', () => {
    const { result } = renderHook(() => useDiagramHistory());

    act(() => result.current.record(null));
    act(() => result.current.record(undefined));

    expect(result.current.canUndo).toBe(false);
  });

  it('caps history so a long session cannot grow without bound', () => {
    const { result } = renderHook(() => useDiagramHistory());

    // One past the 50-entry cap.
    for (let i = 0; i < 51; i += 1) {
      act(() => result.current.record(diagram(`v${i}`)));
    }

    let count = 0;
    let current = diagram('head');
    for (;;) {
      let step;
      act(() => { step = result.current.undo(current); });
      if (!step) break;
      current = step;
      count += 1;
    }

    expect(count).toBe(50);
    // The oldest snapshot was evicted, so the deepest undo is v1, not v0.
    expect(current.nodes[0].label).toBe('v1');
  });

  it('reset clears both stacks', () => {
    const { result } = renderHook(() => useDiagramHistory());

    act(() => result.current.record(diagram('v1')));
    act(() => { result.current.undo(diagram('v2')); });

    act(() => result.current.reset());

    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
  });
});

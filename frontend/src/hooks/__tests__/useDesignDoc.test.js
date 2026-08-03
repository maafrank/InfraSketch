import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';

vi.mock('../../api/client', () => ({
  exportDesignDoc: vi.fn(),
  generateDesignDoc: vi.fn(() => Promise.resolve({ status: 'started' })),
  getDesignDocStatus: vi.fn(),
  pollDesignDocStatus: vi.fn(),
  updateDesignDoc: vi.fn(() => Promise.resolve({})),
}));

import {
  generateDesignDoc,
  getDesignDocStatus,
  pollDesignDocStatus,
} from '../../api/client';
import { useDesignDoc } from '../useDesignDoc';

const deps = {
  sessionId: 'sess-1',
  refreshCredits: vi.fn(),
  refreshGamification: vi.fn(),
  processGamificationResult: vi.fn(),
  setInsufficientCreditsError: vi.fn(),
};

describe('useDesignDoc: not paying twice for the same document', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getDesignDocStatus.mockResolvedValue({ status: 'not_started' });
    pollDesignDocStatus.mockResolvedValue({
      success: true,
      design_doc: '# Fresh',
      is_preview: false,
    });
  });

  it('adopts the existing document instead of generating a second one', async () => {
    // The situation that caused a real regeneration: a doc exists on the server
    // but local state has not hydrated, so `designDoc` is still null.
    getDesignDocStatus.mockResolvedValue({
      status: 'completed',
      design_doc: '# Already generated',
      is_preview: false,
    });

    const { result } = renderHook(() => useDesignDoc(deps));
    await act(() => result.current.handleCreateDesignDoc());

    expect(generateDesignDoc).not.toHaveBeenCalled();
    expect(result.current.designDoc).toBe('# Already generated');
    expect(result.current.designDocOpen).toBe(true);
  });

  it('attaches to a run already in flight rather than starting another', async () => {
    getDesignDocStatus.mockResolvedValue({ status: 'generating' });

    const { result } = renderHook(() => useDesignDoc(deps));
    await act(() => result.current.handleCreateDesignDoc());

    expect(generateDesignDoc).not.toHaveBeenCalled();
    expect(pollDesignDocStatus).toHaveBeenCalledWith('sess-1');
    await waitFor(() => expect(result.current.designDoc).toBe('# Fresh'));
  });

  it('generates when the server confirms there is no document', async () => {
    const { result } = renderHook(() => useDesignDoc(deps));
    await act(() => result.current.handleCreateDesignDoc());

    expect(generateDesignDoc).toHaveBeenCalledWith('sess-1');
    await waitFor(() => expect(result.current.designDoc).toBe('# Fresh'));
  });

  it('still generates if the status probe fails', async () => {
    // A failed probe must not block the user from creating a document.
    getDesignDocStatus.mockRejectedValue(new Error('network'));

    const { result } = renderHook(() => useDesignDoc(deps));
    await act(() => result.current.handleCreateDesignDoc());

    expect(generateDesignDoc).toHaveBeenCalledWith('sess-1');
  });

  it('skips the probe entirely when a doc is already in local state', async () => {
    const { result } = renderHook(() => useDesignDoc(deps));
    act(() => result.current.setDesignDoc('# Local'));

    await act(() => result.current.handleCreateDesignDoc());

    expect(getDesignDocStatus).not.toHaveBeenCalled();
    expect(generateDesignDoc).not.toHaveBeenCalled();
    expect(result.current.designDocOpen).toBe(true);
  });

  it('force still regenerates, bypassing the existing document', async () => {
    // Used after a promo unlocks the full doc for a user who only had a preview.
    getDesignDocStatus.mockResolvedValue({
      status: 'completed',
      design_doc: '# Preview only',
      is_preview: true,
    });

    const { result } = renderHook(() => useDesignDoc(deps));
    await act(() => result.current.handleCreateDesignDoc(true));

    expect(getDesignDocStatus).not.toHaveBeenCalled();
    expect(generateDesignDoc).toHaveBeenCalledWith('sess-1');
  });

  it('hydrating from a session populates the doc so no probe is needed', () => {
    const { result } = renderHook(() => useDesignDoc(deps));

    act(() =>
      result.current.hydrateFromSession({
        design_doc: '# From session',
        design_doc_status: { is_preview: false },
      })
    );

    expect(result.current.designDoc).toBe('# From session');
    // Loading a session must not pop the panel open on its own.
    expect(result.current.designDocOpen).toBe(false);
  });
});

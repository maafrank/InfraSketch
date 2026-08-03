import { useCallback, useState } from 'react';

import {
  exportDesignDoc,
  generateDesignDoc,
  getDesignDocStatus,
  pollDesignDocStatus,
  updateDesignDoc,
} from '../api/client';
import { PANEL_WIDTHS } from '../constants/ui';
import { base64ToBlob, downloadBlob } from '../utils/download';

/**
 * Owns design-doc UI state (panel open/closed, current content, preview flag,
 * width) plus the create/save/export handlers. Lives in App.jsx as a single
 * hook instead of ~5 useState calls + ~120 lines of handler bodies.
 *
 * Cross-cutting deps that aren't owned here (sessionId, credit/gamification
 * refresh, the insufficient-credits modal) are passed in - the hook never
 * pulls them from a global.
 */
export function useDesignDoc({
  sessionId,
  refreshCredits,
  refreshGamification,
  processGamificationResult,
  setInsufficientCreditsError,
}) {
  const [designDoc, setDesignDoc] = useState(null);
  const [designDocOpen, setDesignDocOpen] = useState(false);
  const [designDocLoading, setDesignDocLoading] = useState(false);
  const [designDocWidth, setDesignDocWidth] = useState(PANEL_WIDTHS.designDoc.default);
  const [designDocIsPreview, setDesignDocIsPreview] = useState(false);

  const handleCreateDesignDoc = useCallback(async (forceArg = false) => {
    if (!sessionId) return;

    // Only a literal `true` forces regeneration. Callers wire this straight to
    // onClick, which hands over a MouseEvent; treating that as truthy meant
    // every click wiped the document and paid to generate it again. Narrowing
    // here means a bare onClick can never do that, whatever the call site does.
    const force = forceArg === true;

    // Short-circuit when a doc already exists, unless the caller is forcing a
    // fresh regeneration (e.g. after a FREEDESIGN promo redemption that just
    // unlocked the full doc path for a free user).
    if (designDoc && !force) {
      setDesignDocOpen(true);
      return;
    }

    if (!force) {
      // Local state is not proof that no doc exists. It is empty before a
      // session finishes hydrating, and generating from here would both charge
      // credits and overwrite a document the user already paid for. Confirm
      // against the server first; the status endpoint is free.
      try {
        const existing = await getDesignDocStatus(sessionId);
        if (existing.status === 'completed' && existing.design_doc) {
          setDesignDoc(existing.design_doc);
          setDesignDocIsPreview(existing.is_preview === true);
          setDesignDocOpen(true);
          return;
        }
        if (existing.status === 'generating') {
          // Another tab (or a reload mid-run) already started one. Attach to it
          // rather than paying for a second.
          setDesignDocOpen(true);
          setDesignDocLoading(true);
          const result = await pollDesignDocStatus(sessionId);
          if (result.success) {
            setDesignDocIsPreview(result.is_preview === true);
            setDesignDoc(result.design_doc);
          }
          setDesignDocLoading(false);
          return;
        }
      } catch (error) {
        // Never block generation on a failed status probe.
        console.debug('Design-doc status probe failed, generating:', error);
      }
    }

    if (force) {
      setDesignDoc(null);
      setDesignDocIsPreview(false);
    }

    setDesignDocLoading(true);
    setDesignDocOpen(true);

    try {
      await generateDesignDoc(sessionId);
      const result = await pollDesignDocStatus(sessionId);

      if (result.success) {
        setDesignDocIsPreview(result.is_preview === true);
        setDesignDoc(result.design_doc);
        if (refreshCredits) refreshCredits();
        if (refreshGamification) refreshGamification();
      } else {
        throw new Error(result.error || 'Failed to generate design document');
      }
    } catch (error) {
      console.error('Failed to generate design doc:', error);

      if (error.response?.status === 403 && error.response.data?.error === 'feature_locked') {
        setDesignDocOpen(false);
        setInsufficientCreditsError({
          required: 0,
          available: 0,
          featureLocked: true,
          message: error.response.data.message || 'This feature requires a paid plan.',
        });
      } else if (error.response?.status === 402) {
        const detail = error.response.data?.detail || {};
        setInsufficientCreditsError({
          required: detail.required || 10,
          available: detail.available || 0,
        });
        setDesignDocOpen(false);
      } else {
        alert('Failed to generate design document. Please try again.');
        setDesignDocOpen(false);
      }
    } finally {
      setDesignDocLoading(false);
    }
  }, [sessionId, designDoc, refreshCredits, refreshGamification, setInsufficientCreditsError]);

  const handleSaveDesignDoc = useCallback(async (content) => {
    if (!sessionId) return;
    try {
      await updateDesignDoc(sessionId, content);
      setDesignDoc(content);
    } catch (error) {
      console.error('Failed to save design doc:', error);
      throw error;
    }
  }, [sessionId]);

  const handleExportDesignDoc = useCallback(async (format, diagramImage) => {
    if (!sessionId) return;
    try {
      const response = await exportDesignDoc(sessionId, format, diagramImage);

      if (response.pdf) {
        downloadBlob(base64ToBlob(response.pdf.content, 'application/pdf'), response.pdf.filename);
      }
      if (response.markdown) {
        downloadBlob(new Blob([response.markdown.content], { type: 'text/markdown' }), response.markdown.filename);
      }
      if (response.diagram_png) {
        downloadBlob(base64ToBlob(response.diagram_png.content, 'image/png'), response.diagram_png.filename);
      }

      if (response.gamification && processGamificationResult) {
        processGamificationResult(response.gamification);
      }
    } catch (error) {
      console.error('Failed to export design doc:', error);

      // Export is gated to paid plans. FastAPI nests HTTPException payloads
      // under `detail`, while the doc-generation gate returns a bare body, so
      // accept either shape.
      const body = error.response?.data?.detail ?? error.response?.data ?? {};
      if (error.response?.status === 403 && body.error === 'feature_locked') {
        setInsufficientCreditsError({
          required: 0,
          available: 0,
          featureLocked: true,
          message: body.message || 'Exporting requires a paid plan.',
        });
        return;
      }

      throw error;
    }
  }, [sessionId, processGamificationResult, setInsufficientCreditsError]);

  const handleCloseDesignDoc = useCallback(() => setDesignDocOpen(false), []);

  const handleDesignDocWidthChange = useCallback((width) => setDesignDocWidth(width), []);

  // Hydrate design-doc state when a session is loaded by the session hook.
  const hydrateFromSession = useCallback((sessionData) => {
    setDesignDoc(sessionData.design_doc);
    setDesignDocIsPreview(sessionData.design_doc_status?.is_preview === true);
    setDesignDocOpen(false);
  }, []);

  // Reset to a clean slate (used by handleNewDesign and tutorial onResetAppState).
  const reset = useCallback(() => {
    setDesignDoc(null);
    setDesignDocIsPreview(false);
    setDesignDocOpen(false);
  }, []);

  return {
    designDoc,
    designDocOpen,
    designDocLoading,
    designDocWidth,
    designDocIsPreview,
    // Setters exposed for places that mutate design-doc state from outside the hook
    // (tutorial registerCallbacks treats these as injection points).
    setDesignDoc,
    setDesignDocOpen,
    handleCreateDesignDoc,
    handleSaveDesignDoc,
    handleExportDesignDoc,
    handleCloseDesignDoc,
    handleDesignDocWidthChange,
    hydrateFromSession,
    reset,
  };
}

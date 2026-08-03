import { useCallback, useEffect, useState } from 'react';
import { shareSession, unshareSession } from '../api/client';
import './ShareModal.css';

/**
 * Publish a session as a public link.
 *
 * Sharing is minted on open rather than behind a second click: the user already
 * expressed intent by opening this dialog, and a link they have to ask for
 * twice is a link they do not send.
 */
export default function ShareModal({ sessionId, sessionName, onClose }) {
  const [shareUrl, setShareUrl] = useState(null);
  const [allowFork, setAllowFork] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  const publish = useCallback(async (fork) => {
    setLoading(true);
    setError(null);
    try {
      const result = await shareSession(sessionId, fork);
      setShareUrl(result.share_url);
    } catch (err) {
      console.error('Share failed:', err);
      setError('Could not create a share link. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionId) publish(allowFork);
    // Intentionally runs once: toggling allowFork republishes through its own
    // handler, and re-running here would fight that.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const handleToggleFork = useCallback(async () => {
    const next = !allowFork;
    setAllowFork(next);
    await publish(next);
  }, [allowFork, publish]);

  const handleCopy = useCallback(async () => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  }, [shareUrl]);

  const handleUnshare = useCallback(async () => {
    setLoading(true);
    try {
      await unshareSession(sessionId);
      onClose();
    } catch (err) {
      console.error('Unshare failed:', err);
      setError('Could not revoke the link. Please try again.');
      setLoading(false);
    }
  }, [sessionId, onClose]);

  return (
    <div className="share-modal-overlay" onClick={onClose}>
      <div className="share-modal" onClick={(e) => e.stopPropagation()}>
        <div className="share-modal-header">
          <h2>Share this diagram</h2>
          <button className="close-button" onClick={onClose} title="Close">✕</button>
        </div>

        <div className="share-modal-body">
          <p className="share-modal-blurb">
            Anyone with this link can view <strong>{sessionName || 'this diagram'}</strong> without
            signing in. Your chat history and prompts are never included.
          </p>

          {error && <div className="share-modal-error">{error}</div>}

          <div className="share-url-row">
            <input
              className="share-url-input"
              value={loading && !shareUrl ? 'Creating link...' : (shareUrl || '')}
              readOnly
              onFocus={(e) => e.target.select()}
              aria-label="Public share link"
            />
            <button
              className="share-copy-button"
              onClick={handleCopy}
              disabled={!shareUrl || loading}
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>

          <label className="share-toggle-row">
            <input
              type="checkbox"
              checked={allowFork}
              onChange={handleToggleFork}
              disabled={loading}
            />
            <span>
              <strong>Allow copies</strong>
              <span className="share-toggle-hint">
                Viewers can remix this into their own account. Your original is untouched.
              </span>
            </span>
          </label>
        </div>

        <div className="share-modal-footer">
          <button className="share-unshare-button" onClick={handleUnshare} disabled={loading}>
            Stop sharing
          </button>
          <button className="share-done-button" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}

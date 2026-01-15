import { useState, useEffect } from 'react';
import { getUserSessions, renameSession, deleteSession } from '../api/client';
import './SessionHistorySidebar.css';

export default function SessionHistorySidebar({ isOpen, onClose, onSessionSelect, onWidthChange, currentSessionId, sessionNameUpdated, onSessionDeleted }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [width, setWidth] = useState(300);
  const [isResizing, setIsResizing] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [contextMenu, setContextMenu] = useState(null);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editingName, setEditingName] = useState('');

  // Mobile detection
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Load sessions when sidebar opens
  useEffect(() => {
    if (isOpen) {
      loadSessions();
    }
  }, [isOpen]);

  // Reload sessions when session name is updated (for current session)
  useEffect(() => {
    if (isOpen && sessionNameUpdated && currentSessionId) {
      loadSessions();
    }
  }, [sessionNameUpdated, currentSessionId, isOpen]);

  const loadSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getUserSessions();
      setSessions(data.sessions);
    } catch (err) {
      console.error('Failed to load sessions:', err);
      setError('Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  const handleSessionClick = (sessionId) => {
    onSessionSelect(sessionId);
    // Close sidebar on mobile after selection
    if (isMobile) {
      onClose();
    }
  };

  // Resize logic with RAF throttling
  useEffect(() => {
    let rafId = null;
    let pendingWidth = null;

    const handleMouseMove = (e) => {
      if (!isResizing) return;
      e.preventDefault();

      // For LEFT-side panel: width = mouse X position
      const newWidth = e.clientX;

      // Constraints: 200px - 600px
      // Also ensure we don't make the sidebar wider than 40% of viewport
      const maxWidth = Math.min(600, window.innerWidth * 0.4);

      if (newWidth >= 200 && newWidth <= maxWidth) {
        pendingWidth = newWidth;

        if (!rafId) {
          rafId = requestAnimationFrame(() => {
            if (pendingWidth !== null) {
              setWidth(pendingWidth);
              pendingWidth = null;
            }
            rafId = null;
          });
        }
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.userSelect = '';
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
    };

    if (isResizing) {
      document.body.style.userSelect = 'none';
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [isResizing]);

  // Throttled parent notification
  useEffect(() => {
    if (onWidthChange) {
      const timerId = setTimeout(() => {
        onWidthChange(width);
      }, 16);
      return () => clearTimeout(timerId);
    }
  }, [width, onWidthChange]);

  const formatDateCompact = (isoString) => {
    if (!isoString) return 'Unknown';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    // Handle future dates or invalid timestamps
    if (diffDays < 0) return 'Just now';
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const getModelDisplayName = (model) => {
    if (model?.includes('haiku')) return 'Haiku';
    if (model?.includes('sonnet')) return 'Sonnet';
    return model || 'Unknown';
  };

  const handleContextMenu = (e, session) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      sessionId: session.session_id,
      sessionName: session.name,
    });
  };

  const handleRename = () => {
    if (contextMenu) {
      setEditingSessionId(contextMenu.sessionId);
      setEditingName(contextMenu.sessionName || 'Untitled Design');
      setContextMenu(null);
    }
  };

  const handleDelete = async () => {
    if (contextMenu && window.confirm('Are you sure you want to delete this session?')) {
      try {
        const deletedSessionId = contextMenu.sessionId;
        await deleteSession(deletedSessionId);
        await loadSessions(); // Reload after delete
        setContextMenu(null);

        // If the deleted session was the current session, notify parent to reset
        if (deletedSessionId === currentSessionId && onSessionDeleted) {
          onSessionDeleted(deletedSessionId);
        }
      } catch (error) {
        console.error('Failed to delete session:', error);
        alert('Failed to delete session. Please try again.');
      }
    }
  };

  const handleSaveRename = async (sessionId) => {
    try {
      await renameSession(sessionId, editingName);
      setEditingSessionId(null);
      await loadSessions(); // Reload after rename
    } catch (error) {
      console.error('Failed to rename session:', error);
      alert('Failed to rename session. Please try again.');
    }
  };

  const handleCancelRename = () => {
    setEditingSessionId(null);
    setEditingName('');
  };

  // Close context menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setContextMenu(null);
    if (contextMenu) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [contextMenu]);

  if (!isOpen) return null;

  return (
    <div
      className={`session-history-sidebar ${isMobile ? 'mobile-modal' : ''}`}
      style={{ width: isMobile ? '100%' : `${width}px` }}
    >
      {/* Header */}
      <div className="session-history-header">
        <h3>My Diagrams</h3>
        <button
          className="close-button"
          onClick={onClose}
          aria-label="Close session history"
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div className="session-history-content">
        {loading && (
          <div className="session-loading">
            <div className="session-spinner"></div>
            <p>Loading diagrams...</p>
          </div>
        )}

        {error && (
          <div className="session-error">
            <p>{error}</p>
            <button onClick={loadSessions}>Retry</button>
          </div>
        )}

        {!loading && !error && sessions.length === 0 && (
          <div className="session-empty">
            <p>No diagrams yet</p>
            <small>Create your first diagram to get started!</small>
          </div>
        )}

        {!loading && !error && sessions.length > 0 && (
          <div className="session-history-list">
            {sessions.map((session) => (
              <div
                key={session.session_id}
                className={`session-list-item ${currentSessionId === session.session_id ? 'active' : ''}`}
                onClick={() => handleSessionClick(session.session_id)}
                onContextMenu={(e) => handleContextMenu(e, session)}
              >
                <div className="session-item-header">
                  <span className="session-date-compact">
                    {formatDateCompact(session.created_at)}
                  </span>
                  {session.has_design_doc && <span className="doc-badge">📄</span>}
                </div>

                {editingSessionId === session.session_id ? (
                  <div className="session-name-edit">
                    <input
                      type="text"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      onBlur={() => handleSaveRename(session.session_id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveRename(session.session_id);
                        if (e.key === 'Escape') handleCancelRename();
                      }}
                      autoFocus
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                ) : (
                  <div className="session-name-compact">
                    {session.name || 'Untitled Design'}
                  </div>
                )}

                <div className="session-stats-compact">
                  <span>{session.node_count} nodes</span>
                  <span>•</span>
                  <span>{session.edge_count} edges</span>
                </div>

                <div className="session-model-compact">
                  {getModelDisplayName(session.model)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Resize handle (desktop only) */}
      {!isMobile && (
        <div
          className="resize-handle-right"
          onMouseDown={() => setIsResizing(true)}
        />
      )}

      {/* Context menu */}
      {contextMenu && (
        <div
          className="session-context-menu"
          style={{
            position: 'fixed',
            left: `${contextMenu.x}px`,
            top: `${contextMenu.y}px`,
          }}
        >
          <button onClick={handleRename}>Rename</button>
          <button onClick={handleDelete} className="delete-button">Delete</button>
        </div>
      )}
    </div>
  );
}

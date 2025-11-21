import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { SignedIn, SignedOut, SignInButton, UserButton } from "@clerk/clerk-react";
import { useTheme } from '../contexts/ThemeContext';
import { getUserSessions } from '../api/client';
import './SessionHistory.css';

export default function SessionHistory() {
  const { theme } = useTheme();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getUserSessions();
      setSessions(data.sessions);
    } catch (err) {
      console.error('Failed to load sessions:', err);
      setError('Failed to load session history');
    } finally {
      setLoading(false);
    }
  };

  const handleSessionClick = (sessionId) => {
    navigate(`/session/${sessionId}`);
  };

  const handleNewDesign = () => {
    navigate('/');
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'Unknown date';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  const getModelDisplayName = (model) => {
    if (model?.includes('haiku')) return 'Claude Haiku 4.5';
    if (model?.includes('sonnet')) return 'Claude Sonnet 4.5';
    return model || 'Unknown';
  };

  return (
    <div className="session-history-page">
      <header className="app-header">
        <div className="app-title" onClick={handleNewDesign} style={{ cursor: 'pointer' }}>
          <div className="title-with-logo">
            <img
              src={theme === 'dark' ? "/InfraSketchLogoTransparent_02.png" : "/InfraSketchLogoTransparent_01.png"}
              alt="InfraSketch Logo"
              className="app-logo"
            />
            <div className="title-text">
              <h1>InfraSketch</h1>
              <p>AI-Powered System Design Tool</p>
            </div>
          </div>
        </div>
        <div className="header-right">
          <div className="header-buttons">
            <button className="new-design-button" onClick={handleNewDesign}>
              + New Design
            </button>
          </div>
          <div className="auth-buttons">
            <SignedOut>
              <SignInButton mode="modal">
                <button className="sign-in-button">Sign In</button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <UserButton
                appearance={{
                  elements: {
                    avatarBox: { width: 32, height: 32 }
                  }
                }}
              />
            </SignedIn>
          </div>
        </div>
      </header>

      <div className="session-history-content">
        <div className="history-header">
          <h2>My Diagrams</h2>
          <p className="history-subtitle">
            {sessions.length} {sessions.length === 1 ? 'diagram' : 'diagrams'}
          </p>
        </div>

        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading your diagrams...</p>
          </div>
        )}

        {error && (
          <div className="error-state">
            <p>{error}</p>
            <button onClick={loadSessions}>Try Again</button>
          </div>
        )}

        {!loading && !error && sessions.length === 0 && (
          <div className="empty-state">
            <h3>No diagrams yet</h3>
            <p>Create your first system design diagram to get started!</p>
            <button className="new-design-button" onClick={handleNewDesign}>
              + Create New Diagram
            </button>
          </div>
        )}

        {!loading && !error && sessions.length > 0 && (
          <div className="sessions-grid">
            {sessions.map((session) => (
              <div
                key={session.session_id}
                className="session-card"
                onClick={() => handleSessionClick(session.session_id)}
              >
                <div className="session-card-header">
                  <div className="session-date">
                    {formatDate(session.created_at)}
                  </div>
                  <div className="session-model">
                    {getModelDisplayName(session.model)}
                  </div>
                </div>

                <div className="session-name">
                  {session.name || 'Untitled Design'}
                </div>

                <div className="session-stats">
                  <div className="stat">
                    <span className="stat-value">{session.node_count}</span>
                    <span className="stat-label">nodes</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{session.edge_count}</span>
                    <span className="stat-label">edges</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{session.message_count}</span>
                    <span className="stat-label">messages</span>
                  </div>
                </div>

                {session.has_design_doc && (
                  <div className="session-badge">
                    <span className="badge-icon">📄</span>
                    Design Doc
                  </div>
                )}

                <div className="session-card-footer">
                  <span className="resume-hint">Click to resume →</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

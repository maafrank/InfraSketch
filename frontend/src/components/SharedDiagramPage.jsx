import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth, useClerk } from '@clerk/clerk-react';
import { Helmet } from 'react-helmet-async';
import DiagramCanvas from './DiagramCanvas';
import { forkSharedDiagram, getSharedDiagram, setClerkTokenGetter } from '../api/client';
import '../App.css';
import './SharedDiagramPage.css';

const SITE_URL = 'https://infrasketch.net';

/**
 * Public, read-only view of a shared diagram.
 *
 * Renders signed-out. The meta tags here are for completeness and for the
 * in-app experience; the tags that actually drive link unfurls are injected
 * server-side by backend/app/api/routes_share_html.py, because Slack and X read
 * the raw HTML rather than running the app.
 */
export default function SharedDiagramPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { isSignedIn, getToken } = useAuth();
  const { openSignIn } = useClerk();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [forking, setForking] = useState(false);
  const [docOpen, setDocOpen] = useState(false);

  useEffect(() => {
    if (getToken) setClerkTokenGetter(getToken);
  }, [getToken]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const result = await getSharedDiagram(token);
        if (!cancelled) setData(result);
      } catch (err) {
        if (cancelled) return;
        setError(
          err?.response?.status === 404
            ? 'This diagram is not shared, or the link has been revoked.'
            : 'Could not load this diagram. Please try again.'
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [token]);

  const handleFork = useCallback(async () => {
    // Forking creates a session, which needs an owner, so sign-in comes first.
    if (!isSignedIn) {
      openSignIn({ redirectUrl: `/share/${token}` });
      return;
    }
    setForking(true);
    try {
      const result = await forkSharedDiagram(token);
      navigate(`/session/${result.session_id}`);
    } catch (err) {
      console.error('Fork failed:', err);
      setError(
        err?.response?.status === 403
          ? 'The owner has disabled copying for this diagram.'
          : 'Could not copy this diagram. Please try again.'
      );
      setForking(false);
    }
  }, [isSignedIn, openSignIn, token, navigate]);

  if (loading) {
    return (
      <div className="shared-page shared-page-centered">
        <div className="generating-spinner" />
        <p>Loading diagram...</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="shared-page shared-page-centered">
        <h1>Diagram unavailable</h1>
        <p>{error}</p>
        <a className="shared-cta" href="/">Build your own with InfraSketch</a>
      </div>
    );
  }

  const title = `${data.name} - Architecture Diagram | InfraSketch`;
  const description =
    `${data.name}: a system architecture with ${data.node_count} components. Built with InfraSketch.`;

  return (
    <div className="shared-page">
      <Helmet>
        <title>{title}</title>
        <meta name="description" content={description} />
        <link rel="canonical" href={`${SITE_URL}/share/${token}`} />
      </Helmet>

      <header className="shared-header">
        <a className="shared-brand" href="/">InfraSketch</a>
        <div className="shared-title">
          <h1>{data.name}</h1>
          <span className="shared-meta">
            {data.node_count} components, {data.edge_count} connections
          </span>
        </div>
        <div className="shared-actions">
          {data.design_doc && (
            <button className="shared-doc-toggle" onClick={() => setDocOpen((v) => !v)}>
              {docOpen ? 'Hide design doc' : 'View design doc'}
            </button>
          )}
          {data.allow_fork && (
            <button className="shared-cta" onClick={handleFork} disabled={forking}>
              {forking ? 'Copying...' : 'Remix this diagram'}
            </button>
          )}
        </div>
      </header>

      {error && <div className="shared-inline-error">{error}</div>}

      <div className="shared-body">
        <div className="shared-canvas">
          {/* Read-only: no mutation callbacks are passed, so the canvas renders
              without palette, context menus, or editing affordances. */}
          <DiagramCanvas diagram={data.diagram} loading={false} />
        </div>

        {docOpen && data.design_doc && (
          <aside className="shared-doc">
            <pre>{data.design_doc}</pre>
          </aside>
        )}
      </div>

      <footer className="shared-footer">
        <span>Made with InfraSketch, an AI system design tool.</span>
        <a className="shared-cta shared-cta-small" href="/">Design your own architecture</a>
      </footer>
    </div>
  );
}

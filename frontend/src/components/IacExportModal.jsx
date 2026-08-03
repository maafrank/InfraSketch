import { useCallback, useEffect, useState } from 'react';
import { downloadIac, getIacStatus, pollIacStatus, startIacGeneration } from '../api/client';
import { base64ToBlob, downloadBlob } from '../utils/download';
import './IacExportModal.css';

// Kept in step with CREDIT_COSTS["iac_export"] in
// backend/app/billing/credit_costs.py, so the cost is shown before the click.
const IAC_CREDIT_COST = 10;

const TARGETS = [
  {
    id: 'terraform',
    label: 'Terraform',
    blurb: 'AWS resources, variables, and outputs.',
    language: 'hcl',
  },
  {
    id: 'kubernetes',
    label: 'Kubernetes',
    blurb: 'Deployments, Services, and Ingress manifests.',
    language: 'yaml',
  },
  {
    id: 'compose',
    label: 'Docker Compose',
    blurb: 'A local development stack for this system.',
    language: 'yaml',
  },
];

/**
 * Infrastructure-as-Code export.
 *
 * Generation is an async backend job (30-90s), so this drives the same
 * start-then-poll flow the design doc uses. The output is deliberately framed
 * as a scaffold, both here and in a header comment inside every file: handing
 * someone LLM-written infrastructure that looks authoritative but is wrong is
 * worse than handing them nothing.
 */
export default function IacExportModal({ sessionId, onClose, onCreditsUpdated, onUpgradeNeeded }) {
  const [target, setTarget] = useState('terraform');
  const [artifact, setArtifact] = useState(null);
  const [isStale, setIsStale] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeFile, setActiveFile] = useState(0);
  const [downloading, setDownloading] = useState(false);
  const [copiedPath, setCopiedPath] = useState(null);

  // Load anything already generated for this target so switching tabs does not
  // re-charge for work the session already paid for.
  useEffect(() => {
    let cancelled = false;
    setArtifact(null);
    setError(null);
    setActiveFile(0);

    if (!sessionId) return undefined;

    (async () => {
      try {
        const status = await getIacStatus(sessionId, target);
        if (cancelled) return;
        if (status.artifact) {
          setArtifact(status.artifact);
          setIsStale(status.is_stale === true);
        }
      } catch (err) {
        console.error('Failed to load existing IaC:', err);
      }
    })();

    return () => { cancelled = true; };
  }, [sessionId, target]);

  const handleGenerate = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      await startIacGeneration(sessionId, target);
      const result = await pollIacStatus(sessionId, target);
      if (result.success) {
        setArtifact(result.artifact);
        setIsStale(result.isStale);
        setActiveFile(0);
      } else {
        setError(result.error || 'Generation failed. Please try again.');
      }
      if (onCreditsUpdated) onCreditsUpdated();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (err?.response?.status === 402 || err?.response?.status === 403) {
        // Hand off to the app's existing upgrade modal rather than duplicating it.
        if (onUpgradeNeeded) onUpgradeNeeded(detail);
        onClose();
        return;
      }
      setError(detail?.message || 'Could not start generation. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [sessionId, target, onCreditsUpdated, onUpgradeNeeded, onClose]);

  const handleDownload = useCallback(async () => {
    if (!sessionId || !artifact) return;
    setDownloading(true);
    try {
      const result = await downloadIac(sessionId, target);
      const blob = base64ToBlob(result.zip.content, 'application/zip');
      downloadBlob(blob, result.zip.filename);
    } catch (err) {
      console.error('IaC download failed:', err);
      setError('Could not build the download. Please try again.');
    } finally {
      setDownloading(false);
    }
  }, [sessionId, target, artifact]);

  const handleCopy = useCallback(async (file) => {
    try {
      await navigator.clipboard.writeText(file.content);
      setCopiedPath(file.path);
      setTimeout(() => setCopiedPath(null), 1500);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  }, []);

  const files = artifact?.files || [];
  const current = files[activeFile];

  return (
    <div className="iac-modal-overlay" onClick={onClose}>
      <div className="iac-modal" onClick={(e) => e.stopPropagation()}>
        <div className="iac-modal-header">
          <h2>Export as Infrastructure Code</h2>
          <button className="close-button" onClick={onClose} title="Close">✕</button>
        </div>

        <div className="iac-targets">
          {TARGETS.map((t) => (
            <button
              key={t.id}
              className={`iac-target ${target === t.id ? 'active' : ''}`}
              onClick={() => setTarget(t.id)}
              disabled={loading}
            >
              <span className="iac-target-label">{t.label}</span>
              <span className="iac-target-blurb">{t.blurb}</span>
            </button>
          ))}
        </div>

        <p className="iac-disclaimer">
          Generated code is a <strong>scaffold, not production infrastructure</strong>.
          Review every resource, size it for your real load, and supply your own
          networking, IAM, and secrets before applying it.
        </p>

        <div className="iac-body">
          {loading && (
            <div className="iac-status">
              <div className="generating-spinner" />
              <h3>Generating {TARGETS.find((t) => t.id === target)?.label}...</h3>
              <p>This usually takes under a minute.</p>
            </div>
          )}

          {!loading && error && <div className="iac-status iac-error">{error}</div>}

          {!loading && !error && !artifact && (
            <div className="iac-status">
              <p>No {TARGETS.find((t) => t.id === target)?.label} generated for this diagram yet.</p>
              <button className="iac-generate-button" onClick={handleGenerate}>
                Generate ({IAC_CREDIT_COST} credits)
              </button>
            </div>
          )}

          {!loading && !error && artifact && (
            <>
              {isStale && (
                <div className="iac-stale-banner">
                  The diagram has changed since these files were generated.
                  <button className="iac-stale-regen" onClick={handleGenerate}>
                    Regenerate ({IAC_CREDIT_COST} credits)
                  </button>
                </div>
              )}

              {artifact.assumptions?.length > 0 && (
                <details className="iac-notes" open>
                  <summary>Assumptions ({artifact.assumptions.length})</summary>
                  <ul>
                    {artifact.assumptions.map((a, i) => <li key={i}>{a}</li>)}
                  </ul>
                </details>
              )}

              {artifact.warnings?.length > 0 && (
                <details className="iac-notes iac-notes-warning" open>
                  <summary>Warnings ({artifact.warnings.length})</summary>
                  <ul>
                    {artifact.warnings.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                </details>
              )}

              <div className="iac-files">
                <ul className="iac-file-list">
                  {files.map((file, index) => (
                    <li key={file.path}>
                      <button
                        className={`iac-file-tab ${index === activeFile ? 'active' : ''}`}
                        onClick={() => setActiveFile(index)}
                      >
                        {file.path}
                      </button>
                    </li>
                  ))}
                </ul>

                {current && (
                  <div className="iac-file-view">
                    <div className="iac-file-view-header">
                      <span className="iac-file-path">{current.path}</span>
                      <button className="iac-copy-button" onClick={() => handleCopy(current)}>
                        {copiedPath === current.path ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                    <pre className="iac-code"><code>{current.content}</code></pre>
                  </div>
                )}
              </div>

              <div className="iac-footer">
                <button className="iac-regen-button" onClick={handleGenerate}>
                  Regenerate ({IAC_CREDIT_COST} credits)
                </button>
                <button
                  className="iac-generate-button"
                  onClick={handleDownload}
                  disabled={downloading}
                >
                  {downloading ? 'Preparing...' : `Download .zip (${files.length} files)`}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

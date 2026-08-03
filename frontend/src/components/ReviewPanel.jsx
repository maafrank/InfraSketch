import { useCallback, useEffect, useState } from 'react';
import { MOBILE_BREAKPOINT } from '../constants/ui';
import './ReviewPanel.css';

// Kept in step with CREDIT_COSTS["architecture_review"] in
// backend/app/billing/credit_costs.py. Shown on every button that spends it, so
// a re-run is never a surprise charge.
const REVIEW_CREDIT_COST = 5;

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low'];

const SEVERITY_LABEL = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
};

const CATEGORY_LABEL = {
  reliability: 'Reliability',
  scalability: 'Scalability',
  security: 'Security',
  data: 'Data',
  cost: 'Cost',
  observability: 'Observability',
};

function scoreBand(score) {
  if (score >= 85) return 'strong';
  if (score >= 65) return 'fair';
  return 'weak';
}

/**
 * Architecture review results.
 *
 * Mirrors DesignDocPanel's shell (left-docked, resizable, fullscreen on mobile)
 * so the two panels feel like the same surface. The value here is the two
 * actions on each finding: highlight the nodes it refers to, and hand the
 * recommendation to the chat agent, which can already edit the diagram.
 */
export default function ReviewPanel({
  review,
  isGenerating = false,
  isStale = false,
  error = null,
  onClose,
  onRerun,
  onHighlightNodes,
  onFixFinding,
  onWidthChange,
  // Total width of everything docked to this panel's left: the session-history
  // sidebar plus the design-doc panel when it is open. Both are position:fixed
  // at left:0, so without this offset the two panels sit on top of each other
  // and only the later one in the DOM is visible.
  leftOffset = 0,
}) {
  const [width, setWidth] = useState(420);
  const [isResizing, setIsResizing] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    if (onWidthChange) onWidthChange(isMobile ? 0 : width);
  }, [width, isMobile, onWidthChange]);

  // RAF-throttled drag resize, matching the other panels.
  useEffect(() => {
    if (!isResizing) return;

    let frame = null;
    const handleMouseMove = (e) => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        const next = e.clientX - leftOffset;
        setWidth(Math.min(720, Math.max(320, next)));
        frame = null;
      });
    };
    const handleMouseUp = () => setIsResizing(false);

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, leftOffset]);

  const handleToggleFinding = useCallback((finding) => {
    const nextId = expandedId === finding.id ? null : finding.id;
    setExpandedId(nextId);
    // Collapsing clears the highlight so the canvas doesn't keep a stale glow.
    if (onHighlightNodes) {
      onHighlightNodes(nextId ? finding.node_ids : []);
    }
  }, [expandedId, onHighlightNodes]);

  // Never leave the canvas highlighted after the panel goes away.
  useEffect(() => () => {
    if (onHighlightNodes) onHighlightNodes([]);
  }, [onHighlightNodes]);

  const findings = review?.findings || [];
  const counts = review?.counts || {};

  return (
    <div
      className={`review-panel ${isMobile ? 'mobile-modal' : ''}`}
      style={isMobile ? {} : { width: `${width}px`, left: `${leftOffset}px` }}
    >
      {!isMobile && (
        <div className="resize-handle-right" onMouseDown={() => setIsResizing(true)} />
      )}

      <div className="review-header">
        <h3>Architecture Review</h3>
        <button className="close-button" onClick={onClose} title="Close">✕</button>
      </div>

      <div className="review-body">
        {isGenerating && (
          <div className="review-generating">
            <div className="generating-spinner" />
            <h3>Reviewing your architecture...</h3>
            <p>Sketch is looking for single points of failure, scaling limits, and security gaps. This usually takes under a minute.</p>
          </div>
        )}

        {!isGenerating && error && (
          <div className="review-empty">
            <p className="review-error">{error}</p>
            <button className="review-rerun-button" onClick={onRerun}>
              Try again ({REVIEW_CREDIT_COST} credits)
            </button>
          </div>
        )}

        {!isGenerating && !error && !review && (
          <div className="review-empty">
            <p>No review yet for this diagram.</p>
            <button className="review-rerun-button" onClick={onRerun}>
              Run review ({REVIEW_CREDIT_COST} credits)
            </button>
          </div>
        )}

        {!isGenerating && !error && review && (
          <>
            {isStale && (
              <div className="review-stale-banner">
                <span>
                  The diagram has changed since this review ran, so these findings may
                  no longer match what is on the canvas.
                </span>
                <button className="review-stale-rerun" onClick={onRerun}>
                  Re-run ({REVIEW_CREDIT_COST} credits)
                </button>
              </div>
            )}

            <div className={`review-score review-score-${scoreBand(review.score)}`}>
              <div className="review-score-value">{review.score}</div>
              <div className="review-score-meta">
                <span className="review-score-label">Design score</span>
                <div className="review-severity-chips">
                  {SEVERITY_ORDER.filter((s) => counts[s] > 0).map((severity) => (
                    <span key={severity} className={`review-chip review-chip-${severity}`}>
                      {counts[severity]} {SEVERITY_LABEL[severity].toLowerCase()}
                    </span>
                  ))}
                  {findings.length === 0 && (
                    <span className="review-chip review-chip-clean">No issues found</span>
                  )}
                </div>
              </div>
            </div>

            {review.summary && <p className="review-summary">{review.summary}</p>}

            {findings.length === 0 ? (
              <div className="review-empty">
                <p>Sketch did not find anything worth flagging at this scale. Add more detail to the diagram for a deeper review.</p>
              </div>
            ) : (
              <ul className="review-findings">
                {findings.map((finding) => {
                  const isExpanded = expandedId === finding.id;
                  return (
                    <li
                      key={finding.id}
                      className={`review-finding review-finding-${finding.severity} ${isExpanded ? 'expanded' : ''}`}
                    >
                      <button
                        className="review-finding-header"
                        onClick={() => handleToggleFinding(finding)}
                        aria-expanded={isExpanded}
                      >
                        <span className={`review-badge review-badge-${finding.severity}`}>
                          {SEVERITY_LABEL[finding.severity]}
                        </span>
                        <span className="review-finding-title">{finding.title}</span>
                        <span className="review-finding-category">
                          {CATEGORY_LABEL[finding.category] || finding.category}
                        </span>
                      </button>

                      {isExpanded && (
                        <div className="review-finding-body">
                          {finding.detail && <p>{finding.detail}</p>}
                          {finding.recommendation && (
                            <p className="review-recommendation">
                              <strong>Recommended:</strong> {finding.recommendation}
                            </p>
                          )}
                          {finding.node_ids?.length > 0 && (
                            <p className="review-finding-nodes">
                              Affects: {finding.node_ids.join(', ')}
                            </p>
                          )}
                          <button
                            className="review-fix-button"
                            onClick={() => onFixFinding && onFixFinding(finding)}
                          >
                            Ask Sketch to fix this
                          </button>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}

            <div className="review-footer">
              <button className="review-rerun-button" onClick={onRerun}>
                Re-run review ({REVIEW_CREDIT_COST} credits)
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

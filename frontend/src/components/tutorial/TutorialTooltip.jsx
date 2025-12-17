/**
 * TutorialTooltip - Positioned tooltip showing step instructions.
 */

import React, { useRef, useEffect, useState } from 'react';
import './TutorialTooltip.css';

const TutorialTooltip = ({
  title,
  content,
  position,
  showNavigation = true,
  showLoading = false,
  onNext,
  onPrev,
  canGoBack = true,
  canGoForward = false,
  isLastStep = false,
}) => {
  const tooltipRef = useRef(null);
  const [adjustedPosition, setAdjustedPosition] = useState(position);

  // Adjust position to keep tooltip in viewport
  useEffect(() => {
    if (!tooltipRef.current || !position) return;

    const tooltip = tooltipRef.current;
    const rect = tooltip.getBoundingClientRect();
    const padding = 16;

    let x = position.x;
    let y = position.y;
    const placement = position.placement || 'bottom';

    // Adjust horizontal position
    if (placement === 'left') {
      x = position.x - rect.width;
    } else if (placement === 'right') {
      // Already at right position
    } else {
      // Center horizontally for top/bottom/center
      x = position.x - rect.width / 2;
    }

    // Adjust vertical position
    if (placement === 'top') {
      y = position.y - rect.height;
    } else if (placement === 'center') {
      y = position.y - rect.height / 2;
    } else if (placement === 'left' || placement === 'right') {
      y = position.y - rect.height / 2;
    }

    // Keep in viewport
    if (x < padding) x = padding;
    if (x + rect.width > window.innerWidth - padding) {
      x = window.innerWidth - rect.width - padding;
    }
    if (y < padding) y = padding;
    if (y + rect.height > window.innerHeight - padding) {
      y = window.innerHeight - rect.height - padding;
    }

    setAdjustedPosition({ x, y, placement });
  }, [position]);

  if (!title && !content) return null;

  return (
    <div
      ref={tooltipRef}
      className={`tutorial-tooltip tutorial-tooltip--${adjustedPosition?.placement || 'bottom'}`}
      style={{
        left: adjustedPosition?.x,
        top: adjustedPosition?.y,
      }}
    >
      {/* Arrow */}
      <div className="tutorial-tooltip-arrow" />

      {/* Content */}
      <div className="tutorial-tooltip-content">
        {title && <h3 className="tutorial-tooltip-title">{title}</h3>}
        {content && <p className="tutorial-tooltip-text">{content}</p>}

        {showLoading && (
          <div className="tutorial-tooltip-loading">
            <div className="tutorial-loading-spinner" />
            <span>Processing...</span>
          </div>
        )}
      </div>

      {/* Navigation buttons */}
      {showNavigation && (
        <div className="tutorial-tooltip-nav">
          <button
            className="tutorial-nav-btn tutorial-nav-btn--prev"
            onClick={onPrev}
            disabled={!canGoBack}
          >
            Previous
          </button>
          <button
            className="tutorial-nav-btn tutorial-nav-btn--next"
            onClick={onNext}
            disabled={!canGoForward}
          >
            {isLastStep ? 'Done' : 'Next'}
          </button>
        </div>
      )}
    </div>
  );
};

export default TutorialTooltip;

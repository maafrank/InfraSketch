/**
 * TutorialWelcome - Welcome and completion modal components.
 */

import React from 'react';
import './TutorialWelcome.css';

const TutorialWelcome = ({ modalType, title, content, onAction, onSkip }) => {
  const isCompletion = modalType === 'completion';

  return (
    <div className="tutorial-welcome-backdrop">
      <div className={`tutorial-welcome-modal ${isCompletion ? 'tutorial-welcome-modal--completion' : ''}`}>
        {/* Logo */}
        <div className="tutorial-welcome-logo">
          <img
            src="/InfraSketchLogoTransparent_01_256.png"
            alt="InfraSketch"
            width="80"
            height="80"
          />
        </div>

        {/* Title */}
        <h2 className="tutorial-welcome-title">{title}</h2>

        {/* Content */}
        <p className="tutorial-welcome-content">{content}</p>

        {/* Features list for welcome modal */}
        {!isCompletion && (
          <div className="tutorial-welcome-features">
            <div className="tutorial-welcome-feature">
              <span className="tutorial-welcome-feature-icon">1</span>
              <span>Generate diagrams with AI</span>
            </div>
            <div className="tutorial-welcome-feature">
              <span className="tutorial-welcome-feature-icon">2</span>
              <span>Edit with natural language</span>
            </div>
            <div className="tutorial-welcome-feature">
              <span className="tutorial-welcome-feature-icon">3</span>
              <span>Export design documents</span>
            </div>
          </div>
        )}

        {/* Completion stats */}
        {isCompletion && (
          <div className="tutorial-welcome-stats">
            <div className="tutorial-welcome-stat">
              <span className="tutorial-welcome-stat-value">9</span>
              <span className="tutorial-welcome-stat-label">Features learned</span>
            </div>
            <div className="tutorial-welcome-stat">
              <span className="tutorial-welcome-stat-value">~2</span>
              <span className="tutorial-welcome-stat-label">Minutes spent</span>
            </div>
          </div>
        )}

        {/* Action button */}
        <button className="tutorial-welcome-button" onClick={onAction}>
          {isCompletion ? 'Start Designing' : 'Start Tour'}
        </button>

        {/* Estimated time and skip link */}
        {!isCompletion && (
          <>
            <p className="tutorial-welcome-time">Takes about 2 minutes</p>
            {onSkip && (
              <button className="tutorial-welcome-skip" onClick={onSkip}>
                Skip tutorial
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default TutorialWelcome;

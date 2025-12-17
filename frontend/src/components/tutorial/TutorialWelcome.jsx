/**
 * TutorialWelcome - Welcome and completion modal components.
 */

import React from 'react';
import './TutorialWelcome.css';

const TutorialWelcome = ({ modalType, title, content, onAction }) => {
  const isCompletion = modalType === 'completion';

  return (
    <div className="tutorial-welcome-backdrop">
      <div className={`tutorial-welcome-modal ${isCompletion ? 'tutorial-welcome-modal--completion' : ''}`}>
        {/* Icon */}
        <div className="tutorial-welcome-icon">
          {isCompletion ? (
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="32" cy="32" r="30" fill="url(#gradient)" />
              <path
                d="M20 32L28 40L44 24"
                stroke="white"
                strokeWidth="4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <defs>
                <linearGradient id="gradient" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#667eea" />
                  <stop offset="1" stopColor="#9f7aea" />
                </linearGradient>
              </defs>
            </svg>
          ) : (
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="32" cy="32" r="30" fill="url(#gradient2)" />
              <path
                d="M32 18V32L40 40"
                stroke="white"
                strokeWidth="4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M32 18C32 18 24 22 24 32C24 42 32 46 32 46"
                stroke="white"
                strokeWidth="3"
                strokeLinecap="round"
                opacity="0.5"
              />
              <path
                d="M32 18C32 18 40 22 40 32C40 42 32 46 32 46"
                stroke="white"
                strokeWidth="3"
                strokeLinecap="round"
                opacity="0.5"
              />
              <defs>
                <linearGradient id="gradient2" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#667eea" />
                  <stop offset="1" stopColor="#9f7aea" />
                </linearGradient>
              </defs>
            </svg>
          )}
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

        {/* Estimated time */}
        {!isCompletion && (
          <p className="tutorial-welcome-time">Takes about 2 minutes</p>
        )}
      </div>
    </div>
  );
};

export default TutorialWelcome;

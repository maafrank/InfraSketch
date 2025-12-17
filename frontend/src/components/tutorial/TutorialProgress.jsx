/**
 * TutorialProgress - Progress indicator showing current step and phase.
 */

import React from 'react';
import './TutorialProgress.css';

const PHASE_NAMES = [
  '', // Phase 0 doesn't exist
  'Getting Started',
  'Edit with Chat',
  'Add Components',
  'Connections',
  'Grouping',
  'Canvas Tools',
  'Design Doc',
  'History',
  'Finish',
];

const TutorialProgress = ({
  currentStep,
  totalSteps,
  currentPhase,
  totalPhases,
}) => {
  const progressPercent = ((currentStep + 1) / totalSteps) * 100;

  return (
    <div className="tutorial-progress">
      {/* Phase indicator */}
      <div className="tutorial-progress-phase">
        <span className="tutorial-progress-phase-label">
          Phase {currentPhase} of {totalPhases}
        </span>
        <span className="tutorial-progress-phase-name">
          {PHASE_NAMES[currentPhase] || ''}
        </span>
      </div>

      {/* Progress bar */}
      <div className="tutorial-progress-bar">
        <div
          className="tutorial-progress-bar-fill"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Step counter */}
      <div className="tutorial-progress-steps">
        Step {currentStep + 1} of {totalSteps}
      </div>
    </div>
  );
};

export default TutorialProgress;

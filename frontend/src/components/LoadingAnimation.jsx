import { useState, useEffect } from 'react';

export default function LoadingAnimation() {
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    { icon: '🤔', text: 'Analyzing your architecture...', duration: 2500 },
    { icon: '🏗️', text: 'Designing system components...', duration: 2500 },
    { icon: '🔗', text: 'Mapping connections and data flow...', duration: 2500 },
    { icon: '⚙️', text: 'Optimizing component placement...', duration: 2500 },
    { icon: '🎨', text: 'Generating visual layout...', duration: 2500 },
    { icon: '✨', text: 'Finalizing your diagram...', duration: 2500 },
  ];

  useEffect(() => {
    // Calculate total duration
    const totalDuration = steps.reduce((acc, step) => acc + step.duration, 0);
    let elapsedTime = 0;

    const interval = setInterval(() => {
      elapsedTime += 100;

      // Find which step we should be on based on elapsed time
      let accumulatedTime = 0;
      let nextStep = 0;

      for (let i = 0; i < steps.length; i++) {
        accumulatedTime += steps[i].duration;
        if (elapsedTime < accumulatedTime) {
          nextStep = i;
          break;
        }
      }

      // Stay on the last step if we exceed total duration
      if (elapsedTime >= totalDuration) {
        nextStep = steps.length - 1;
      }

      setCurrentStep(nextStep);
    }, 100);

    return () => clearInterval(interval);
  }, []);

  // Calculate progress percentage
  const getProgress = () => {
    const completedSteps = currentStep;
    const totalSteps = steps.length;
    return (completedSteps / totalSteps) * 100;
  };

  return (
    <div className="loading-animation">
      <div className="loading-content">
        <div className="loading-icon-container">
          <div className="loading-icon">{steps[currentStep].icon}</div>
          <div className="loading-spinner"></div>
        </div>

        <h3 className="loading-title">Building Your System Architecture</h3>

        <p className="loading-step">{steps[currentStep].text}</p>

        <div className="loading-progress-bar">
          <div
            className="loading-progress-fill"
            style={{ width: `${getProgress()}%` }}
          ></div>
        </div>

        <div className="loading-steps-list">
          {steps.map((step, index) => (
            <div
              key={index}
              className={`loading-step-item ${index === currentStep ? 'active' : ''} ${index < currentStep ? 'completed' : ''}`}
            >
              <span className="step-icon">{step.icon}</span>
              <span className="step-text">{step.text}</span>
              {index < currentStep && <span className="step-check">✓</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

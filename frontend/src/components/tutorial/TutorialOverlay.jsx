/**
 * TutorialOverlay - Main overlay component that renders the spotlight and tooltip.
 * Handles positioning and coordinates all tutorial UI elements.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useTutorial } from '../../contexts/useTutorial';
import TutorialTooltip from './TutorialTooltip';
import TutorialWelcome from './TutorialWelcome';
import TutorialProgress from './TutorialProgress';
import './TutorialOverlay.css';

const TutorialOverlay = () => {
  const {
    isActive,
    isLoading,
    currentStep,
    currentStepIndex,
    totalSteps,
    currentPhase,
    totalPhases,
    nextStep,
    prevStep,
  } = useTutorial();

  const [spotlightRect, setSpotlightRect] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const overlayRef = useRef(null);

  // Calculate spotlight position based on target element
  const updateSpotlightPosition = useCallback(() => {
    if (!currentStep || currentStep.type === 'modal') {
      setSpotlightRect(null);
      return;
    }

    const target = currentStep.target;
    if (!target) {
      setSpotlightRect(null);
      return;
    }

    const element = document.querySelector(target);
    if (!element) {
      // Target not found - might be loading, retry later
      console.log('Tutorial target not found:', target);
      setSpotlightRect(null);
      return;
    }

    const rect = element.getBoundingClientRect();
    const padding = 8; // Padding around the highlighted element

    setSpotlightRect({
      top: rect.top - padding,
      left: rect.left - padding,
      width: rect.width + padding * 2,
      height: rect.height + padding * 2,
    });

    // Calculate tooltip position based on placement
    const placement = currentStep.placement || 'bottom';
    const tooltipOffset = 16;
    let tooltipX, tooltipY;

    switch (placement) {
      case 'top':
        tooltipX = rect.left + rect.width / 2;
        tooltipY = rect.top - tooltipOffset;
        break;
      case 'bottom':
        tooltipX = rect.left + rect.width / 2;
        tooltipY = rect.bottom + tooltipOffset;
        break;
      case 'left':
        tooltipX = rect.left - tooltipOffset;
        tooltipY = rect.top + rect.height / 2;
        break;
      case 'right':
        tooltipX = rect.right + tooltipOffset;
        tooltipY = rect.top + rect.height / 2;
        break;
      case 'center':
        tooltipX = window.innerWidth / 2;
        tooltipY = window.innerHeight / 2;
        break;
      default:
        tooltipX = rect.left + rect.width / 2;
        tooltipY = rect.bottom + tooltipOffset;
    }

    setTooltipPosition({ x: tooltipX, y: tooltipY, placement });
  }, [currentStep]);

  // Update position on step change and window resize
  useEffect(() => {
    if (!isActive) return;

    // Small delay to allow React to render any modals/elements first
    const initialTimer = setTimeout(() => {
      updateSpotlightPosition();
    }, 50);

    // Also update immediately in case element is already rendered
    updateSpotlightPosition();

    // Also update on resize and scroll
    const handleResize = () => updateSpotlightPosition();
    window.addEventListener('resize', handleResize);
    window.addEventListener('scroll', handleResize, true);

    // Retry position update if element not found or has zero dimensions
    const retryTimer = setInterval(() => {
      if (currentStep && currentStep.target) {
        const element = document.querySelector(currentStep.target);
        if (!element) {
          updateSpotlightPosition();
        } else {
          // Also retry if element has zero dimensions (might still be animating in)
          const rect = element.getBoundingClientRect();
          if (rect.width === 0 || rect.height === 0) {
            updateSpotlightPosition();
          }
        }
      }
    }, 200);

    return () => {
      clearTimeout(initialTimer);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('scroll', handleResize, true);
      clearInterval(retryTimer);
    };
  }, [isActive, currentStep, updateSpotlightPosition]);

  // Don't render anything if not active or loading
  if (isLoading || !isActive) {
    return null;
  }

  // Render welcome/completion modal
  if (currentStep?.type === 'modal') {
    return (
      <div className="tutorial-overlay" ref={overlayRef}>
        <div className="tutorial-backdrop" />
        <TutorialWelcome
          modalType={currentStep.modalType}
          title={currentStep.title}
          content={currentStep.content}
          onAction={() => nextStep()}
        />
      </div>
    );
  }

  // Render spotlight with tooltip
  return (
    <div className="tutorial-overlay" ref={overlayRef}>
      {/* Dark backdrop with spotlight hole */}
      <div className="tutorial-backdrop">
        {spotlightRect && (
          <div
            className="tutorial-spotlight"
            style={{
              top: spotlightRect.top,
              left: spotlightRect.left,
              width: spotlightRect.width,
              height: spotlightRect.height,
            }}
          />
        )}
      </div>

      {/* Tooltip */}
      <TutorialTooltip
        title={currentStep?.title}
        content={currentStep?.content}
        position={tooltipPosition}
        showNavigation={true}
        showLoading={currentStep?.showLoading}
        onNext={nextStep}
        onPrev={prevStep}
        canGoBack={currentStepIndex > 0}
        canGoForward={true}
        isLastStep={currentStep?.isLastStep}
      />

      {/* Progress indicator */}
      <TutorialProgress
        currentStep={currentStepIndex}
        totalSteps={totalSteps}
        currentPhase={currentPhase}
        totalPhases={totalPhases}
      />
    </div>
  );
};

export default TutorialOverlay;

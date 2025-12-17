/**
 * Tutorial Context - State machine for the onboarding tutorial.
 * Manages tutorial state, step progression, and coordinates with App.jsx.
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { TUTORIAL_STEPS, getPhaseNumber, TOTAL_PHASES } from '../data/tutorialSteps';
import { getUserPreferences, completeTutorial as apiCompleteTutorial } from '../api/client';

const TutorialContext = createContext(null);

export const useTutorial = () => {
  const context = useContext(TutorialContext);
  if (!context) {
    throw new Error('useTutorial must be used within a TutorialProvider');
  }
  return context;
};

export const TutorialProvider = ({ children, isSignedIn, isMobile }) => {
  // Core state
  const [isActive, setIsActive] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [hasCompleted, setHasCompleted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [awaitingUserAction, setAwaitingUserAction] = useState(false);

  // Current step
  const currentStep = TUTORIAL_STEPS[currentStepIndex] || null;
  const totalSteps = TUTORIAL_STEPS.length;
  const currentPhase = currentStep ? getPhaseNumber(currentStepIndex) : 1;

  // Callbacks to be set by App.jsx for state injection
  const [onDiagramChange, setOnDiagramChange] = useState(() => () => {});
  const [onMessagesChange, setOnMessagesChange] = useState(() => () => {});
  const [onDesignDocChange, setOnDesignDocChange] = useState(() => () => {});
  const [onPrefillChat, setOnPrefillChat] = useState(() => () => {});
  const [onShowDesignDocPanel, setOnShowDesignDocPanel] = useState(() => () => {});
  const [onShowHistoryPanel, setOnShowHistoryPanel] = useState(() => () => {});
  const [onOpenAddNodeModal, setOnOpenAddNodeModal] = useState(() => () => {});

  // Cleanup callbacks - called when advancing to clean up state from previous step
  const [onClearChatPrefill, setOnClearChatPrefill] = useState(() => () => {});
  const [onCloseAddNodeModal, setOnCloseAddNodeModal] = useState(() => () => {});
  const [onCloseDesignDocPanel, setOnCloseDesignDocPanel] = useState(() => () => {});
  const [onCloseHistoryPanel, setOnCloseHistoryPanel] = useState(() => () => {});

  // Reset app state callback - called when tutorial completes
  const [onResetAppState, setOnResetAppState] = useState(() => () => {});

  // Check tutorial status on mount (when signed in)
  useEffect(() => {
    const checkTutorialStatus = async () => {
      // Skip tutorial on mobile
      if (isMobile) {
        setIsLoading(false);
        setHasCompleted(true);
        return;
      }

      if (!isSignedIn) {
        setIsLoading(false);
        return;
      }

      try {
        const prefs = await getUserPreferences();
        setHasCompleted(prefs.tutorial_completed);

        // Auto-start tutorial for new users
        if (!prefs.tutorial_completed) {
          setIsActive(true);
          setCurrentStepIndex(0);
        }
      } catch (error) {
        console.error('Failed to fetch user preferences:', error);
        // Fail open - don't block the app if preferences fail
        setHasCompleted(true);
      } finally {
        setIsLoading(false);
      }
    };

    checkTutorialStatus();
  }, [isSignedIn, isMobile]);

  // Track last applied step to prevent re-applying effects
  const [lastAppliedStepIndex, setLastAppliedStepIndex] = useState(-1);

  // Apply step state changes (diagram, messages, etc.) - only when step changes
  useEffect(() => {
    if (!isActive || !currentStep) return;

    // Only apply effects once per step
    if (currentStepIndex === lastAppliedStepIndex) return;
    setLastAppliedStepIndex(currentStepIndex);

    // Apply diagram state if specified
    if (currentStep.diagramState && onDiagramChange) {
      onDiagramChange(currentStep.diagramState);
    }

    // Apply messages state if specified
    if (currentStep.messagesState && onMessagesChange) {
      onMessagesChange(currentStep.messagesState);
    }

    // Apply design doc state if specified
    if (currentStep.designDocState && onDesignDocChange) {
      onDesignDocChange(currentStep.designDocState);
    }

    // Show design doc panel if specified
    if (currentStep.showDesignDocPanel && onShowDesignDocPanel) {
      onShowDesignDocPanel(true);
    }

    // Show history panel if specified
    if (currentStep.showHistoryPanel && onShowHistoryPanel) {
      onShowHistoryPanel(true);
    }

    // Prefill chat input if specified
    if (currentStep.prefillText && onPrefillChat) {
      onPrefillChat(currentStep.prefillText);
    }

    // Open and prefill add node modal if specified
    if (currentStep.prefillNode && onOpenAddNodeModal) {
      onOpenAddNodeModal(currentStep.prefillNode);
    }

    // Set awaiting action based on step type
    setAwaitingUserAction(currentStep.action ? true : false);
  }, [
    isActive,
    currentStepIndex,
    lastAppliedStepIndex,
    currentStep,
    onDiagramChange,
    onMessagesChange,
    onDesignDocChange,
    onShowDesignDocPanel,
    onShowHistoryPanel,
    onPrefillChat,
    onOpenAddNodeModal,
  ]);

  // Start the tutorial
  const startTutorial = useCallback(() => {
    setIsActive(true);
    setCurrentStepIndex(0);
    setAwaitingUserAction(false);
  }, []);

  // Go to next step
  const nextStep = useCallback(() => {
    // Clean up state from current step before advancing
    if (currentStep?.prefillText) {
      onClearChatPrefill();
    }
    if (currentStep?.prefillNode) {
      onCloseAddNodeModal();
    }
    if (currentStep?.showDesignDocPanel) {
      onCloseDesignDocPanel();
    }
    if (currentStep?.showHistoryPanel) {
      onCloseHistoryPanel();
    }

    if (currentStepIndex < totalSteps - 1) {
      setCurrentStepIndex(prev => prev + 1);
      setAwaitingUserAction(false);
    } else {
      // Tutorial complete
      completeTutorial();
    }
  }, [currentStepIndex, totalSteps, currentStep, onClearChatPrefill, onCloseAddNodeModal, onCloseDesignDocPanel, onCloseHistoryPanel]);

  // Go to previous step
  const prevStep = useCallback(() => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
      setAwaitingUserAction(false);
    }
  }, [currentStepIndex]);

  // Complete the tutorial
  const completeTutorial = useCallback(async () => {
    setIsActive(false);
    setHasCompleted(true);

    // Reset app to clean "new design" state
    onResetAppState();

    // Persist to backend
    try {
      await apiCompleteTutorial();
    } catch (error) {
      console.error('Failed to save tutorial completion:', error);
    }
  }, [onResetAppState]);

  // Reset tutorial (for replaying from settings)
  const resetTutorial = useCallback(() => {
    setHasCompleted(false);
    setCurrentStepIndex(0);
    setIsActive(true);
  }, []);

  // Handle user action (called by App.jsx when user performs expected action)
  const handleUserAction = useCallback((action, payload = null) => {
    if (!isActive || !currentStep) return false;

    // Check if this action matches the expected action
    if (currentStep.action === action) {
      // For node clicks, verify the correct node was clicked
      if (action === 'click-node' && currentStep.expectedNodeId) {
        if (payload?.nodeId !== currentStep.expectedNodeId) {
          return false; // Wrong node clicked
        }
      }

      // Action matched - advance to next step
      nextStep();
      return true;
    }

    return false;
  }, [isActive, currentStep, nextStep]);

  // Check if an action should be intercepted by the tutorial
  const shouldInterceptAction = useCallback((action) => {
    if (!isActive || !currentStep) return false;
    return currentStep.action === action;
  }, [isActive, currentStep]);

  // Register callbacks from App.jsx
  const registerCallbacks = useCallback((callbacks) => {
    // State injection callbacks
    if (callbacks.onDiagramChange) setOnDiagramChange(() => callbacks.onDiagramChange);
    if (callbacks.onMessagesChange) setOnMessagesChange(() => callbacks.onMessagesChange);
    if (callbacks.onDesignDocChange) setOnDesignDocChange(() => callbacks.onDesignDocChange);
    if (callbacks.onPrefillChat) setOnPrefillChat(() => callbacks.onPrefillChat);
    if (callbacks.onShowDesignDocPanel) setOnShowDesignDocPanel(() => callbacks.onShowDesignDocPanel);
    if (callbacks.onShowHistoryPanel) setOnShowHistoryPanel(() => callbacks.onShowHistoryPanel);
    if (callbacks.onOpenAddNodeModal) setOnOpenAddNodeModal(() => callbacks.onOpenAddNodeModal);
    // Cleanup callbacks
    if (callbacks.onClearChatPrefill) setOnClearChatPrefill(() => callbacks.onClearChatPrefill);
    if (callbacks.onCloseAddNodeModal) setOnCloseAddNodeModal(() => callbacks.onCloseAddNodeModal);
    if (callbacks.onCloseDesignDocPanel) setOnCloseDesignDocPanel(() => callbacks.onCloseDesignDocPanel);
    if (callbacks.onCloseHistoryPanel) setOnCloseHistoryPanel(() => callbacks.onCloseHistoryPanel);
    // Reset app state callback
    if (callbacks.onResetAppState) setOnResetAppState(() => callbacks.onResetAppState);
  }, []);

  const value = {
    // State
    isActive,
    isLoading,
    hasCompleted,
    currentStep,
    currentStepIndex,
    totalSteps,
    currentPhase,
    totalPhases: TOTAL_PHASES,
    awaitingUserAction,

    // Actions
    startTutorial,
    nextStep,
    prevStep,
    completeTutorial,
    resetTutorial,
    handleUserAction,
    shouldInterceptAction,
    registerCallbacks,
  };

  return (
    <TutorialContext.Provider value={value}>
      {children}
    </TutorialContext.Provider>
  );
};

export default TutorialContext;

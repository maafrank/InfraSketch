/**
 * Tutorial step definitions.
 * Each step defines what to highlight, what message to show, and what action to wait for.
 *
 * Simplified tutorial: 5 steps covering core value proposition.
 * Users can discover advanced features (manual nodes, connections, grouping, etc.) naturally.
 */

import {
  TUTORIAL_DIAGRAM,
  TUTORIAL_DIAGRAM_WITH_RATE_LIMITER,
  TUTORIAL_INITIAL_MESSAGES,
  TUTORIAL_RATE_LIMITER_MESSAGES,
  TUTORIAL_PROMPTS,
} from './tutorialContent';

/**
 * Step types:
 * - 'modal': Full-screen modal (welcome/completion)
 * - 'spotlight': Highlight an element with tooltip
 */

export const TUTORIAL_STEPS = [
  // ==========================================================================
  // PHASE 1: Welcome & Generate
  // ==========================================================================
  {
    id: 'welcome',
    phase: 1,
    type: 'modal',
    modalType: 'welcome',
    title: 'Welcome to InfraSketch!',
    content: 'Design system architectures with AI in seconds. Let me show you how it works.',
    action: 'click-start',
  },
  {
    id: 'generate-diagram',
    phase: 1,
    type: 'spotlight',
    target: '.chat-input-form textarea',
    title: 'Describe Your System',
    content: 'Press Enter or click send to generate your architecture diagram.',
    prefillText: TUTORIAL_PROMPTS.initial,
    action: 'submit-chat',
    placement: 'left',
  },

  // ==========================================================================
  // PHASE 2: Edit with Chat
  // ==========================================================================
  {
    id: 'edit-via-chat',
    phase: 2,
    type: 'spotlight',
    target: '.chat-input-form textarea',
    title: 'Modify with Chat',
    content: 'Ask the AI to change your diagram. Press Enter to add rate limiting.',
    prefillText: TUTORIAL_PROMPTS.addRateLimiter,
    action: 'submit-chat',
    placement: 'left',
    // Apply the initial diagram when entering this step (simulates generation)
    diagramState: TUTORIAL_DIAGRAM,
    messagesState: TUTORIAL_INITIAL_MESSAGES,
  },

  // ==========================================================================
  // PHASE 3: Design Doc & Completion
  // ==========================================================================
  {
    id: 'design-doc',
    phase: 3,
    type: 'spotlight',
    target: '.create-design-doc-button',
    title: 'Generate Documentation',
    content: 'Click to create a comprehensive design document from your diagram.',
    action: 'click-design-doc',
    placement: 'bottom',
    // Apply the updated diagram when entering this step (simulates chat edit)
    diagramState: TUTORIAL_DIAGRAM_WITH_RATE_LIMITER,
    messagesState: TUTORIAL_RATE_LIMITER_MESSAGES,
  },
  {
    id: 'completion',
    phase: 3,
    type: 'modal',
    modalType: 'completion',
    title: "You're Ready!",
    content: 'You now know the essentials. Explore on your own to discover more features.',
    action: 'click-start',
    isLastStep: true,
  },
];

// Helper to get step by ID
export const getStepById = (id) => TUTORIAL_STEPS.find(step => step.id === id);

// Helper to get current phase number
export const getPhaseNumber = (stepIndex) => {
  const step = TUTORIAL_STEPS[stepIndex];
  return step ? step.phase : 1;
};

// Total number of phases
export const TOTAL_PHASES = 3;

// Get all steps for a specific phase
export const getStepsForPhase = (phase) => TUTORIAL_STEPS.filter(step => step.phase === phase);

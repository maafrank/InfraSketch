/**
 * Tutorial step definitions.
 * Each step defines what to highlight, what message to show, and what action to wait for.
 */

import {
  TUTORIAL_DIAGRAM,
  TUTORIAL_DIAGRAM_WITH_RATE_LIMITER,
  TUTORIAL_DIAGRAM_WITH_REDIS,
  TUTORIAL_DIAGRAM_WITH_CONNECTION,
  TUTORIAL_DIAGRAM_WITH_GROUP,
  TUTORIAL_DIAGRAM_WITH_GROUP_EXPANDED,
  TUTORIAL_INITIAL_MESSAGES,
  TUTORIAL_RATE_LIMITER_MESSAGES,
  TUTORIAL_DESIGN_DOC,
  TUTORIAL_PROMPTS,
  TUTORIAL_MANUAL_NODE,
} from './tutorialContent';

/**
 * Step types:
 * - 'modal': Full-screen modal (welcome/completion)
 * - 'spotlight': Highlight an element with tooltip
 * - 'info': Just show tooltip without requiring action
 */

export const TUTORIAL_STEPS = [
  // ==========================================================================
  // PHASE 1: Welcome & Initial Generation
  // ==========================================================================
  {
    id: 'welcome',
    phase: 1,
    type: 'modal',
    modalType: 'welcome',
    title: 'Welcome to InfraSketch!',
    content: 'Let me show you how to design system architectures with AI. This quick tour will walk you through all the features.',
    action: 'click-start',
  },
  {
    id: 'prefill-prompt',
    phase: 1,
    type: 'spotlight',
    target: '.chat-input-form textarea',
    title: 'Describe Your System',
    content: 'I\'ve pre-filled an example prompt. Press Enter or click the send button to generate your first diagram.',
    prefillText: TUTORIAL_PROMPTS.initial,
    action: 'submit-chat',
    placement: 'left',
  },
  {
    id: 'diagram-ready',
    phase: 1,
    type: 'info',
    target: '.diagram-canvas',
    title: 'Your Diagram is Ready!',
    content: 'Here\'s your system architecture! Each box represents a component. The lines show how they connect.',
    diagramState: TUTORIAL_DIAGRAM,
    messagesState: TUTORIAL_INITIAL_MESSAGES,
    placement: 'center',
  },

  // ==========================================================================
  // PHASE 2: Conversational Editing
  // ==========================================================================
  {
    id: 'edit-request',
    phase: 2,
    type: 'spotlight',
    target: '.chat-input-form textarea',
    title: 'Request Changes',
    content: 'You can ask the AI to modify the diagram. Press Enter to add rate limiting.',
    prefillText: TUTORIAL_PROMPTS.addRateLimiter,
    action: 'submit-chat',
    placement: 'left',
  },
  {
    id: 'diagram-updated',
    phase: 2,
    type: 'info',
    target: '.diagram-canvas',
    title: 'Diagram Updated!',
    content: 'The AI added a Rate Limiter component. Notice how it automatically connected it to the existing services.',
    diagramState: TUTORIAL_DIAGRAM_WITH_RATE_LIMITER,
    messagesState: TUTORIAL_RATE_LIMITER_MESSAGES,
    placement: 'center',
  },

  // ==========================================================================
  // PHASE 3: Manual Node Creation
  // ==========================================================================
  {
    id: 'add-node-intro',
    phase: 3,
    type: 'spotlight',
    target: '.add-node-button',
    title: 'Add Components Manually',
    content: 'Click the "Add Node" button to manually add components to your diagram.',
    action: 'click-add-node',
    placement: 'bottom',
  },
  {
    id: 'add-node-form',
    phase: 3,
    type: 'spotlight',
    target: '.modal-content',
    title: 'Fill in Details',
    content: 'I\'ve pre-filled a Product Cache component. Click "Add Node" to add it to your diagram.',
    action: 'submit-add-node',
    prefillNode: TUTORIAL_MANUAL_NODE,
    placement: 'right',
  },
  {
    id: 'node-added',
    phase: 3,
    type: 'info',
    target: '.diagram-canvas',
    title: 'Node Added!',
    content: 'Great! You\'ve manually added a cache component. You can also use the palette at the bottom for quick access.',
    diagramState: TUTORIAL_DIAGRAM_WITH_REDIS,
    placement: 'center',
  },

  // ==========================================================================
  // PHASE 4: Creating Connections
  // ==========================================================================
  {
    id: 'connection-intro',
    phase: 4,
    type: 'spotlight',
    target: '[data-id="user-db"] .react-flow__handle-bottom',
    title: 'Create Connections',
    content: 'Drag from the bottom handle of User Database to connect it to another node. Try connecting it to the Session Cache.',
    action: 'create-edge',
    placement: 'right',
  },
  {
    id: 'connection-created',
    phase: 4,
    type: 'info',
    target: '.diagram-canvas',
    title: 'Connection Created!',
    content: 'You\'ve created a new connection between components. Connections show data flow in your architecture.',
    diagramState: TUTORIAL_DIAGRAM_WITH_CONNECTION,
    placement: 'center',
  },

  // ==========================================================================
  // PHASE 5: Grouping Nodes (Drag-to-Merge)
  // ==========================================================================
  {
    id: 'group-intro',
    phase: 5,
    type: 'spotlight',
    target: '[data-id="user-db"]',
    title: 'Group Related Components',
    content: 'Drag the User Database onto the Product Database to group them together. This helps organize complex diagrams.',
    action: 'merge-nodes',
    placement: 'right',
  },
  {
    id: 'group-created',
    phase: 5,
    type: 'info',
    target: '.diagram-canvas',
    title: 'Group Created!',
    content: 'The databases are now grouped together. Groups help organize your diagram and can be collapsed to reduce clutter.',
    diagramState: TUTORIAL_DIAGRAM_WITH_GROUP,
    placement: 'center',
  },
  {
    id: 'group-collapse',
    phase: 5,
    type: 'spotlight',
    target: '[data-id="databases-group"] .group-collapse-btn',
    title: 'Expand/Collapse Groups',
    content: 'Click the arrow button to expand or collapse the group. This shows or hides the grouped components.',
    diagramState: TUTORIAL_DIAGRAM_WITH_GROUP_EXPANDED,
    action: 'toggle-group',
    placement: 'right',
  },

  // ==========================================================================
  // PHASE 6: Canvas Tools (Floating Buttons)
  // ==========================================================================
  {
    id: 'tools-intro',
    phase: 6,
    type: 'spotlight',
    target: '.floating-buttons',
    title: 'Canvas Tools',
    content: 'These buttons help you organize and export your diagram. Let me show you each one.',
    placement: 'left',
  },
  {
    id: 'layout-button',
    phase: 6,
    type: 'spotlight',
    target: '.floating-layout-button',
    title: 'Auto-Layout',
    content: 'Click to automatically organize your diagram in a clean, hierarchical layout.',
    action: 'click-layout',
    placement: 'left',
  },
  {
    id: 'direction-button',
    phase: 6,
    type: 'spotlight',
    target: '.floating-direction-button',
    title: 'Toggle Direction',
    content: 'Switch between vertical and horizontal layouts. Click to try it!',
    action: 'click-direction',
    placement: 'left',
  },
  {
    id: 'screenshot-button',
    phase: 6,
    type: 'info',
    target: '.floating-camera-button',
    title: 'Export as Image',
    content: 'Click the camera button anytime to download your diagram as a PNG image.',
    placement: 'left',
  },
  {
    id: 'expand-all-button',
    phase: 6,
    type: 'info',
    target: '.floating-expand-button',
    title: 'Expand/Collapse All',
    content: 'Quickly expand or collapse all groups in your diagram with one click.',
    placement: 'left',
  },

  // ==========================================================================
  // PHASE 7: Design Document
  // ==========================================================================
  {
    id: 'design-doc-intro',
    phase: 7,
    type: 'spotlight',
    target: '.create-design-doc-button',
    title: 'Generate Documentation',
    content: 'Click to generate a comprehensive design document from your diagram.',
    action: 'click-design-doc',
    placement: 'bottom',
  },
  {
    id: 'design-doc-panel',
    phase: 7,
    type: 'info',
    target: '.design-doc-panel',
    title: 'Design Document',
    content: 'The AI generates detailed documentation including architecture overview, component details, and security considerations.',
    designDocState: TUTORIAL_DESIGN_DOC,
    showDesignDocPanel: true,
    placement: 'left',
  },
  {
    id: 'export-options',
    phase: 7,
    type: 'spotlight',
    target: '.export-dropdown',
    title: 'Export Options',
    content: 'Export your documentation as PDF, Markdown, or just the diagram image. Perfect for sharing with your team!',
    showDesignDocPanel: true,
    placement: 'top',
  },

  // ==========================================================================
  // PHASE 8: Session History
  // ==========================================================================
  {
    id: 'history-intro',
    phase: 8,
    type: 'spotlight',
    target: '.history-toggle-button',
    title: 'Session History',
    content: 'Click to open your saved designs. All your work is automatically saved.',
    action: 'click-history',
    placement: 'right',
  },
  {
    id: 'history-panel',
    phase: 8,
    type: 'info',
    title: 'Your Designs',
    content: 'Access all your previous designs here. Click any session to load it, or right-click to rename or delete.',
    showHistoryPanel: true,
    placement: 'center',
  },

  // ==========================================================================
  // PHASE 9: Settings & Completion
  // ==========================================================================
  {
    id: 'model-selector',
    phase: 9,
    type: 'info',
    target: '.model-select',
    title: 'Choose Your AI Model',
    content: 'Select between Haiku (faster) and Sonnet (more detailed) depending on your needs.',
    placement: 'bottom',
  },
  {
    id: 'theme-toggle',
    phase: 9,
    type: 'info',
    target: '.theme-toggle',
    title: 'Dark/Light Mode',
    content: 'Toggle between dark and light themes based on your preference.',
    placement: 'bottom',
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
export const TOTAL_PHASES = 9;

// Get all steps for a specific phase
export const getStepsForPhase = (phase) => TUTORIAL_STEPS.filter(step => step.phase === phase);

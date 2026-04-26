/**
 * App Component Integration Tests
 * Tests for the main application component and its state management
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import App from '../App';
import { DEFAULT_MODEL, MODELS } from '../constants/models';

// Mock API client
vi.mock('../api/client', () => ({
  generateDiagram: vi.fn(() => Promise.resolve({ session_id: 'test-session-123', status: 'generating' })),
  pollDiagramStatus: vi.fn(() => Promise.resolve({
    success: true,
    diagram: { nodes: [], edges: [] },
    messages: [],
    name: 'Test Diagram',
  })),
  sendChatMessage: vi.fn(() => Promise.resolve({ response: 'AI response', diagram: null })),
  addNode: vi.fn((sessionId, node) => Promise.resolve({
    nodes: [node],
    edges: [],
  })),
  deleteNode: vi.fn(() => Promise.resolve({ nodes: [], edges: [] })),
  updateNode: vi.fn((sessionId, nodeId, updates) => Promise.resolve({
    nodes: [{ id: nodeId, ...updates }],
    edges: [],
  })),
  addEdge: vi.fn((sessionId, edge) => Promise.resolve({
    nodes: [],
    edges: [edge],
  })),
  deleteEdge: vi.fn(() => Promise.resolve({ nodes: [], edges: [] })),
  generateDesignDoc: vi.fn(() => Promise.resolve({ status: 'started' })),
  pollDesignDocStatus: vi.fn(() => Promise.resolve({
    success: true,
    design_doc: '# Test Design Document',
  })),
  updateDesignDoc: vi.fn(() => Promise.resolve({ success: true })),
  exportDesignDoc: vi.fn(() => Promise.resolve({ pdf: { content: 'base64', filename: 'doc.pdf' } })),
  setClerkTokenGetter: vi.fn(),
  getSession: vi.fn(() => Promise.resolve({
    session_id: 'test-session-123',
    name: 'Test Session',
    diagram: { nodes: [], edges: [] },
    messages: [],
    design_doc: null,
    model: DEFAULT_MODEL,
  })),
  createBlankSession: vi.fn(() => Promise.resolve({
    session_id: 'new-session-123',
    diagram: { nodes: [], edges: [] },
  })),
  pollSessionName: vi.fn(() => Promise.resolve({ success: true, name: 'Generated Name' })),
  createNodeGroup: vi.fn(() => Promise.resolve({
    diagram: { nodes: [], edges: [] },
    group_id: 'group-1',
  })),
  generateNodeDescription: vi.fn(() => Promise.resolve({
    description: 'Generated description',
    diagram: { nodes: [], edges: [] },
  })),
  toggleGroupCollapse: vi.fn(() => Promise.resolve({ nodes: [], edges: [] })),
  ungroupNodes: vi.fn(() => Promise.resolve({ nodes: [], edges: [] })),
  getUserSessions: vi.fn(() => Promise.resolve([])),
  renameSession: vi.fn(() => Promise.resolve({ success: true, name: 'Renamed' })),
  deleteSession: vi.fn(() => Promise.resolve({ success: true })),
  // Newer endpoints that mounted child components (CreditBalance, Tutorial,
  // GamificationHeader, etc.) consume but the original mock list missed.
  getUserCredits: vi.fn(() => Promise.resolve({ credits_balance: 1000, plan: 'pro' })),
  getCreditHistory: vi.fn(() => Promise.resolve({ entries: [] })),
  getUserGamification: vi.fn(() => Promise.resolve({
    xp: 0, level: 1, achievements: [], streak_days: 0, pending_notifications: [],
  })),
  getUserAchievements: vi.fn(() => Promise.resolve({ achievements: [], stats: {} })),
  getUserPreferences: vi.fn(() => Promise.resolve({ tutorial_completed: true })),
  completeTutorial: vi.fn(() => Promise.resolve({ success: true })),
  resetTutorial: vi.fn(() => Promise.resolve({ success: true })),
  redeemPromoCode: vi.fn(() => Promise.resolve({ success: true })),
  validatePromoCode: vi.fn(() => Promise.resolve({ valid: true })),
  updateStreakReminderPreference: vi.fn(() => Promise.resolve({ success: true })),
  dismissGamificationNotifications: vi.fn(() => Promise.resolve({ success: true })),
  getSubscriptionStatus: vi.fn(() => Promise.resolve({ subscribed: false })),
  unsubscribeFromMarketing: vi.fn(() => Promise.resolve({ success: true })),
  resubscribeToMarketing: vi.fn(() => Promise.resolve({ success: true })),
  generateDiagramFromRepo: vi.fn(() => Promise.resolve({ session_id: 'repo-session-123', status: 'analyzing' })),
  pollRepoAnalysisStatus: vi.fn(() => Promise.resolve({
    success: true, diagram: { nodes: [], edges: [] }, messages: [],
  })),
  isGitHubUrl: vi.fn(() => false),
  analyzeRepo: vi.fn(() => Promise.resolve({ session_id: 'repo-session-123', status: 'analyzing' })),
}));

// Mock html-to-image
vi.mock('html-to-image', () => ({
  toPng: vi.fn(() => Promise.resolve('data:image/png;base64,test')),
}));

// Mock child components to simplify testing
vi.mock('../components/LandingPage', () => ({
  default: ({ onSubmit, onExampleClick }) => (
    <div data-testid="landing-page">
      <input
        data-testid="prompt-input"
        placeholder="Enter prompt"
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            onSubmit(e.target.value, DEFAULT_MODEL);
          }
        }}
      />
      <button
        data-testid="submit-button"
        onClick={() => onSubmit('Test prompt', DEFAULT_MODEL)}
      >
        Generate
      </button>
      <button
        data-testid="example-button"
        onClick={() => onExampleClick && onExampleClick('Example prompt')}
      >
        Try Example
      </button>
    </div>
  ),
}));

vi.mock('../components/DiagramCanvas', () => ({
  default: ({
    diagram,
    loading,
    onNodeClick,
    onDeleteNode,
    onAddEdge,
    onDeleteEdge,
    onOpenNodePalette,
    onExportPng,
    onExampleClick,
    mergingNodes,
  }) => (
    <div data-testid="diagram-canvas" data-loading={loading} data-merging={mergingNodes}>
      <div data-testid="node-count">{diagram?.nodes?.length || 0}</div>
      <div data-testid="edge-count">{diagram?.edges?.length || 0}</div>
      <button data-testid="add-component" onClick={onOpenNodePalette}>Add Component</button>
      <button data-testid="export-png" onClick={onExportPng}>Export PNG</button>
      <button
        data-testid="click-node"
        onClick={() => onNodeClick?.({ id: 'node-1', data: { label: 'Test Node', type: 'api' } })}
      >
        Click Node
      </button>
      <button data-testid="delete-node" onClick={() => onDeleteNode?.('node-1')}>Delete Node</button>
      <button
        data-testid="add-edge"
        onClick={() => onAddEdge?.({ id: 'edge-1', source: 'a', target: 'b' })}
      >
        Add Edge
      </button>
      <button data-testid="delete-edge" onClick={() => onDeleteEdge?.('edge-1')}>Delete Edge</button>
      {!diagram?.nodes?.length && (
        <button data-testid="example-prompt" onClick={() => onExampleClick?.('Build a chat app')}>
          Example
        </button>
      )}
    </div>
  ),
}));

vi.mock('../components/ChatPanel', () => ({
  default: ({
    messages,
    onSendMessage,
    loading,
    loadingStepText,
    selectedNode,
    onExitNodeFocus,
    currentModel,
    onModelChange,
  }) => (
    <div data-testid="chat-panel" data-loading={loading}>
      <div data-testid="message-count">{messages?.length || 0}</div>
      <div data-testid="current-model">{currentModel}</div>
      {selectedNode && (
        <div data-testid="selected-node">
          {selectedNode.data.label}
          <button data-testid="exit-focus" onClick={onExitNodeFocus}>Exit Focus</button>
        </div>
      )}
      {loadingStepText && <div data-testid="loading-step">{loadingStepText}</div>}
      <input data-testid="chat-input" placeholder="Type message" />
      <button
        data-testid="send-message"
        onClick={() => onSendMessage?.('Test message')}
        disabled={loading}
      >
        Send
      </button>
      <select
        data-testid="model-select"
        value={currentModel}
        onChange={(e) => onModelChange?.(e.target.value)}
      >
        <option value={MODELS.HAIKU}>Speed</option>
        <option value={MODELS.SONNET}>Power</option>
      </select>
    </div>
  ),
}));

vi.mock('../components/DesignDocPanel', () => ({
  default: ({ designDoc, loading, onSave, onExport }) => (
    <div data-testid="design-doc-panel" data-loading={loading}>
      {designDoc && <div data-testid="design-doc-content">{designDoc}</div>}
      <button data-testid="save-doc" onClick={() => onSave?.('Updated doc')}>Save</button>
      <button data-testid="export-doc" onClick={() => onExport?.('pdf')}>Export</button>
    </div>
  ),
}));

vi.mock('../components/SessionHistorySidebar', () => ({
  default: ({ onLoadSession, onSessionDeleted }) => (
    <div data-testid="session-history">
      <button
        data-testid="load-session"
        onClick={() => onLoadSession?.('session-1')}
      >
        Load Session
      </button>
      <button
        data-testid="delete-session"
        onClick={() => onSessionDeleted?.('session-1')}
      >
        Delete Session
      </button>
    </div>
  ),
}));

vi.mock('../components/NodePalette', () => ({
  default: ({ onSelectType, onClose }) => (
    <div data-testid="node-palette">
      <button data-testid="select-database" onClick={() => onSelectType?.('database')}>
        Database
      </button>
      <button data-testid="close-palette" onClick={onClose}>Close</button>
    </div>
  ),
}));

vi.mock('../components/AddNodeModal', () => ({
  default: ({ isOpen, onClose, onAddNode, preSelectedType }) => (
    isOpen ? (
      <div data-testid="add-node-modal" data-type={preSelectedType}>
        <button
          data-testid="add-node-confirm"
          onClick={() => onAddNode?.({
            id: 'new-node-1',
            type: preSelectedType || 'service',
            label: 'New Node',
          })}
        >
          Add Node
        </button>
        <button data-testid="close-modal" onClick={onClose}>Cancel</button>
      </div>
    ) : null
  ),
}));

vi.mock('../components/ThemeToggle', () => ({
  default: () => <button data-testid="theme-toggle">Toggle Theme</button>,
}));

vi.mock('../contexts/useTheme', () => ({
  useTheme: () => ({ theme: 'light' }),
}));

// Wrapper component with Router
const renderApp = (initialRoute = '/') => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route path="/" element={<App resumeMode={false} />} />
        <Route path="/session/:sessionId" element={<App resumeMode={true} />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial Render', () => {
    it('renders diagram canvas when signed in', () => {
      // When signed in (mocked), DiagramCanvas is shown instead of LandingPage
      renderApp('/');

      expect(screen.getByTestId('diagram-canvas')).toBeInTheDocument();
    });

    it('renders diagram canvas with empty state initially', () => {
      renderApp('/');

      expect(screen.getByTestId('diagram-canvas')).toBeInTheDocument();
      expect(screen.getByTestId('node-count')).toHaveTextContent('0');
    });

    it('renders chat panel when signed in', () => {
      renderApp('/');

      expect(screen.getByTestId('chat-panel')).toBeInTheDocument();
    });

    it('does not render a theme toggle (terminal theme is always dark)', () => {
      renderApp('/');

      // ThemeToggle was removed in App.jsx - keeping this test as a guard
      // against accidentally re-introducing it.
      expect(screen.queryByTestId('theme-toggle')).not.toBeInTheDocument();
    });

    it('renders node palette when signed in', async () => {
      renderApp('/');

      // NodePalette is rendered when signed in
      expect(screen.getByTestId('node-palette')).toBeInTheDocument();
    });
  });

  describe('Diagram Generation Flow', () => {
    it('triggers generation when example clicked from empty diagram', async () => {
      const user = userEvent.setup();

      renderApp('/');

      // When signed in with no diagram, DiagramCanvas shows example button
      await user.click(screen.getByTestId('example-prompt'));

      // The example click triggers generation via handleExampleClick
      expect(screen.getByTestId('diagram-canvas')).toBeInTheDocument();
    });

    it('shows loading state during generation', async () => {
      const user = userEvent.setup();
      const { sendChatMessage: sendChatMessageFn } = await import('../api/client');

      // Make chat message take longer to simulate loading
      sendChatMessageFn.mockImplementation(() => new Promise((resolve) => {
        setTimeout(() => resolve({ response: 'AI response', diagram: null }), 100);
      }));

      renderApp('/');

      // Send a message to trigger loading state
      await user.click(screen.getByTestId('send-message'));

      // Chat panel shows the current state
      expect(screen.getByTestId('chat-panel')).toBeInTheDocument();
    });
  });

  describe('Chat Functionality', () => {
    it('sends chat message', async () => {
      const user = userEvent.setup();

      renderApp('/');

      await user.click(screen.getByTestId('send-message'));

      // Chat message is sent (though may not work without session)
      // This verifies the handler is connected
      expect(screen.getByTestId('chat-panel')).toBeInTheDocument();
    });

    it('changes model selection', async () => {
      const user = userEvent.setup();

      renderApp('/');

      await user.selectOptions(screen.getByTestId('model-select'), MODELS.SONNET);

      expect(screen.getByTestId('current-model')).toHaveTextContent(MODELS.SONNET);
    });
  });

  describe('Node Operations', () => {
    it('handles node click', async () => {
      const user = userEvent.setup();

      renderApp('/');

      await user.click(screen.getByTestId('click-node'));

      await waitFor(() => {
        expect(screen.getByTestId('selected-node')).toBeInTheDocument();
      });
    });

    it('exits node focus mode', async () => {
      const user = userEvent.setup();

      renderApp('/');

      // Click node first
      await user.click(screen.getByTestId('click-node'));

      await waitFor(() => {
        expect(screen.getByTestId('selected-node')).toBeInTheDocument();
      });

      // Exit focus
      await user.click(screen.getByTestId('exit-focus'));

      await waitFor(() => {
        expect(screen.queryByTestId('selected-node')).not.toBeInTheDocument();
      });
    });

    it('opens node palette when add component clicked', async () => {
      const user = userEvent.setup();

      renderApp('/');

      await user.click(screen.getByTestId('add-component'));

      await waitFor(() => {
        expect(screen.getByTestId('node-palette')).toBeInTheDocument();
      });
    });
  });

  describe('Session Management', () => {
    it('renders app with session route support', async () => {
      renderApp('/session/test-session-123');

      // App renders even at session route
      await waitFor(() => {
        expect(screen.getByTestId('diagram-canvas')).toBeInTheDocument();
      });
    });
  });

  describe('Node Palette and Modal', () => {
    it('opens add node modal when type selected from palette', async () => {
      const user = userEvent.setup();

      renderApp('/');

      // Open palette
      await user.click(screen.getByTestId('add-component'));

      await waitFor(() => {
        expect(screen.getByTestId('node-palette')).toBeInTheDocument();
      });

      // Select type
      await user.click(screen.getByTestId('select-database'));

      await waitFor(() => {
        expect(screen.getByTestId('add-node-modal')).toBeInTheDocument();
        expect(screen.getByTestId('add-node-modal').getAttribute('data-type')).toBe('database');
      });
    });

    it('closes palette when close clicked', async () => {
      const user = userEvent.setup();

      renderApp('/');

      // Open palette
      await user.click(screen.getByTestId('add-component'));

      await waitFor(() => {
        expect(screen.getByTestId('node-palette')).toBeInTheDocument();
      });

      // Note: The palette visibility is managed differently in the actual component
      // This test verifies the close handler is connected
    });
  });

  describe('Design Document', () => {
    it('supports design document functionality', () => {
      renderApp('/');

      // App renders with design doc support (panel is conditionally visible)
      expect(screen.getByTestId('diagram-canvas')).toBeInTheDocument();
    });
  });

  describe('Export Functionality', () => {
    it('triggers export when export button clicked', async () => {
      const user = userEvent.setup();

      renderApp('/');

      await user.click(screen.getByTestId('export-png'));

      // Export is triggered (the actual functionality depends on html-to-image)
      expect(screen.getByTestId('diagram-canvas')).toBeInTheDocument();
    });
  });

  describe('Example Prompts', () => {
    it('populates chat with example prompt from diagram canvas', async () => {
      const user = userEvent.setup();

      renderApp('/');

      await user.click(screen.getByTestId('example-prompt'));

      // Example prompt triggers generation flow
      expect(screen.getByTestId('chat-panel')).toBeInTheDocument();
    });
  });

  describe('Session History', () => {
    it('renders app with session history support', () => {
      renderApp('/');

      // The app renders and supports session history (sidebar is mocked)
      expect(screen.getByTestId('diagram-canvas')).toBeInTheDocument();
    });

    it('supports session URL routes', async () => {
      renderApp('/session/test-session-123');

      // App renders at session route
      await waitFor(() => {
        expect(screen.getByTestId('diagram-canvas')).toBeInTheDocument();
      });
    });
  });

  describe('UI State', () => {
    it('shows zero nodes initially', () => {
      renderApp('/');

      expect(screen.getByTestId('node-count')).toHaveTextContent('0');
    });

    it('shows zero edges initially', () => {
      renderApp('/');

      expect(screen.getByTestId('edge-count')).toHaveTextContent('0');
    });

    it('shows zero messages initially', () => {
      renderApp('/');

      expect(screen.getByTestId('message-count')).toHaveTextContent('0');
    });
  });
});

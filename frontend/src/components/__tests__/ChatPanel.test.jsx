/**
 * ChatPanel Component Tests
 * Tests for the conversational AI chat interface
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatPanel from '../ChatPanel';

// Mock ReactMarkdown to simplify testing
vi.mock('react-markdown', () => ({
  default: ({ children }) => <div data-testid="markdown">{children}</div>,
}));

describe('ChatPanel', () => {
  const defaultProps = {
    selectedNode: null,
    messages: [],
    onSendMessage: vi.fn(),
    loading: false,
    loadingStepText: null,
    onWidthChange: vi.fn(),
    onClose: vi.fn(),
    onExitNodeFocus: vi.fn(),
    examplePrompt: null,
    currentModel: 'claude-haiku-4-5',
    onModelChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset viewport width for consistent tests
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    });
  });

  describe('Basic Rendering', () => {
    it('renders chat panel container', () => {
      render(<ChatPanel {...defaultProps} />);

      // Form element exists (note: form without accessible name doesn't show up as role="form")
      expect(document.querySelector('.chat-panel')).toBeInTheDocument();
      expect(document.querySelector('.chat-input-form')).toBeInTheDocument();
    });

    it('renders model selector with default value', () => {
      render(<ChatPanel {...defaultProps} />);

      const select = screen.getByRole('combobox');
      expect(select).toHaveValue('claude-haiku-4-5');
    });

    it('renders both model options', () => {
      render(<ChatPanel {...defaultProps} />);

      const options = screen.getAllByRole('option');
      expect(options).toHaveLength(2);
      expect(options[0]).toHaveValue('claude-haiku-4-5');
      expect(options[1]).toHaveValue('claude-sonnet-4-5');
    });

    it('renders textarea for input', () => {
      render(<ChatPanel {...defaultProps} />);

      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('renders send button', () => {
      render(<ChatPanel {...defaultProps} />);

      expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
    });

    it('shows default placeholder when no node selected', () => {
      render(<ChatPanel {...defaultProps} />);

      expect(screen.getByPlaceholderText('Ask about the system...')).toBeInTheDocument();
    });
  });

  describe('Message Display', () => {
    it('renders message list', () => {
      const messages = [
        { role: 'user', content: 'Hello' },
        { role: 'assistant', content: 'Hi there!' },
      ];

      render(<ChatPanel {...defaultProps} messages={messages} />);

      expect(screen.getByText('Hello')).toBeInTheDocument();
      expect(screen.getByText('Hi there!')).toBeInTheDocument();
    });

    it('displays message roles', () => {
      const messages = [
        { role: 'user', content: 'Test message' },
        { role: 'assistant', content: 'Response' },
      ];

      render(<ChatPanel {...defaultProps} messages={messages} />);

      const roleLabels = screen.getAllByText(/^(user|assistant)$/);
      expect(roleLabels.length).toBeGreaterThanOrEqual(2);
    });

    it('renders messages with ReactMarkdown', () => {
      const messages = [{ role: 'assistant', content: '**Bold text**' }];

      render(<ChatPanel {...defaultProps} messages={messages} />);

      expect(screen.getByTestId('markdown')).toBeInTheDocument();
    });

    it('shows empty state when no messages', () => {
      render(<ChatPanel {...defaultProps} messages={[]} />);

      // Chat messages area should exist but be empty
      const messagesArea = document.querySelector('.chat-messages');
      expect(messagesArea).toBeInTheDocument();
    });
  });

  describe('Form Submission', () => {
    it('calls onSendMessage when form submitted', async () => {
      const user = userEvent.setup();
      const onSendMessage = vi.fn();

      render(<ChatPanel {...defaultProps} onSendMessage={onSendMessage} />);

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Test message');
      await user.click(screen.getByRole('button', { name: /send/i }));

      expect(onSendMessage).toHaveBeenCalledWith('Test message');
    });

    it('clears input after submission', async () => {
      const user = userEvent.setup();

      render(<ChatPanel {...defaultProps} />);

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Test message');
      await user.click(screen.getByRole('button', { name: /send/i }));

      expect(textarea).toHaveValue('');
    });

    it('does not submit empty message', async () => {
      const user = userEvent.setup();
      const onSendMessage = vi.fn();

      render(<ChatPanel {...defaultProps} onSendMessage={onSendMessage} />);

      await user.click(screen.getByRole('button', { name: /send/i }));

      expect(onSendMessage).not.toHaveBeenCalled();
    });

    it('does not submit whitespace-only message', async () => {
      const user = userEvent.setup();
      const onSendMessage = vi.fn();

      render(<ChatPanel {...defaultProps} onSendMessage={onSendMessage} />);

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, '   ');
      await user.click(screen.getByRole('button', { name: /send/i }));

      expect(onSendMessage).not.toHaveBeenCalled();
    });
  });

  describe('Keyboard Handling', () => {
    it('submits on Enter key', async () => {
      const user = userEvent.setup();
      const onSendMessage = vi.fn();

      render(<ChatPanel {...defaultProps} onSendMessage={onSendMessage} />);

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Test message');
      await user.keyboard('{Enter}');

      expect(onSendMessage).toHaveBeenCalledWith('Test message');
    });

    it('does not submit on Shift+Enter', async () => {
      const user = userEvent.setup();
      const onSendMessage = vi.fn();

      render(<ChatPanel {...defaultProps} onSendMessage={onSendMessage} />);

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Line 1');
      await user.keyboard('{Shift>}{Enter}{/Shift}');
      await user.type(textarea, 'Line 2');

      // Should not have submitted
      expect(onSendMessage).not.toHaveBeenCalled();
    });
  });

  describe('Loading State', () => {
    it('disables send button when loading', () => {
      render(<ChatPanel {...defaultProps} loading={true} />);

      expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
    });

    it('disables model selector when loading', () => {
      render(<ChatPanel {...defaultProps} loading={true} />);

      expect(screen.getByRole('combobox')).toBeDisabled();
    });

    it('shows thinking indicator when loading', () => {
      render(<ChatPanel {...defaultProps} loading={true} />);

      expect(screen.getByText('Thinking...')).toBeInTheDocument();
    });

    it('shows loading step text when provided', () => {
      render(<ChatPanel {...defaultProps} loadingStepText="Analyzing diagram..." />);

      expect(screen.getByText('Analyzing diagram...')).toBeInTheDocument();
    });
  });

  describe('Button Disabled State', () => {
    it('disables send button when input is empty', () => {
      render(<ChatPanel {...defaultProps} />);

      expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
    });

    it('enables send button when input has content', async () => {
      const user = userEvent.setup();

      render(<ChatPanel {...defaultProps} />);

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Test');

      expect(screen.getByRole('button', { name: /send/i })).not.toBeDisabled();
    });
  });

  describe('Model Selection', () => {
    it('calls onModelChange when model selected', async () => {
      const user = userEvent.setup();
      const onModelChange = vi.fn();

      render(<ChatPanel {...defaultProps} onModelChange={onModelChange} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'claude-sonnet-4-5');

      expect(onModelChange).toHaveBeenCalledWith('claude-sonnet-4-5');
    });

    it('displays current model selection', () => {
      render(<ChatPanel {...defaultProps} currentModel="claude-sonnet-4-5" />);

      expect(screen.getByRole('combobox')).toHaveValue('claude-sonnet-4-5');
    });
  });

  describe('Node Focus Mode', () => {
    const selectedNode = {
      id: 'node-1',
      data: {
        label: 'PostgreSQL',
        type: 'database',
        description: 'Main database',
      },
    };

    it('shows node context when node selected', () => {
      render(<ChatPanel {...defaultProps} selectedNode={selectedNode} />);

      // Use getAllByText since PostgreSQL appears in multiple places (context and focus indicator)
      expect(screen.getAllByText(/PostgreSQL/).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/database/)).toBeInTheDocument();
    });

    it('updates placeholder when node selected', () => {
      render(<ChatPanel {...defaultProps} selectedNode={selectedNode} />);

      expect(screen.getByPlaceholderText('Ask about PostgreSQL...')).toBeInTheDocument();
    });

    it('shows node focus indicator on desktop', () => {
      render(<ChatPanel {...defaultProps} selectedNode={selectedNode} />);

      expect(screen.getByText(/Chatting about:/)).toBeInTheDocument();
      expect(screen.getByText('PostgreSQL')).toBeInTheDocument();
    });

    it('shows exit node focus button on desktop', () => {
      render(<ChatPanel {...defaultProps} selectedNode={selectedNode} />);

      expect(screen.getByTitle('Return to system chat')).toBeInTheDocument();
    });

    it('calls onExitNodeFocus when exit button clicked', async () => {
      const user = userEvent.setup();
      const onExitNodeFocus = vi.fn();

      render(
        <ChatPanel
          {...defaultProps}
          selectedNode={selectedNode}
          onExitNodeFocus={onExitNodeFocus}
        />
      );

      await user.click(screen.getByTitle('Return to system chat'));

      expect(onExitNodeFocus).toHaveBeenCalled();
    });
  });

  describe('Example Prompt', () => {
    it('populates input with example prompt', async () => {
      render(<ChatPanel {...defaultProps} examplePrompt="Add a caching layer" />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toHaveValue('Add a caching layer');
      });
    });

    it('updates input when example prompt changes', async () => {
      const { rerender } = render(<ChatPanel {...defaultProps} />);

      expect(screen.getByRole('textbox')).toHaveValue('');

      rerender(<ChatPanel {...defaultProps} examplePrompt="New prompt" />);

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toHaveValue('New prompt');
      });
    });
  });

  describe('Resize Functionality (Desktop)', () => {
    it('renders resize handle on desktop', () => {
      render(<ChatPanel {...defaultProps} />);

      expect(document.querySelector('.resize-handle')).toBeInTheDocument();
    });

    it('notifies parent of width changes', async () => {
      const onWidthChange = vi.fn();

      render(<ChatPanel {...defaultProps} onWidthChange={onWidthChange} />);

      // Initial width notification
      await waitFor(() => {
        expect(onWidthChange).toHaveBeenCalled();
      });
    });
  });

  describe('Mobile Mode', () => {
    beforeEach(() => {
      // Set mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768,
      });
      // Trigger resize event
      fireEvent(window, new Event('resize'));
    });

    it('adds mobile-modal class on mobile viewport', async () => {
      render(<ChatPanel {...defaultProps} />);

      // Wait for mobile detection
      await waitFor(() => {
        const panel = document.querySelector('.chat-panel');
        expect(panel).toHaveClass('mobile-modal');
      });
    });

    it('shows close button on mobile', async () => {
      render(<ChatPanel {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByTitle('Back to diagram')).toBeInTheDocument();
      });
    });

    it('calls onClose when close button clicked on mobile', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(<ChatPanel {...defaultProps} onClose={onClose} />);

      await waitFor(async () => {
        const closeButton = screen.getByTitle('Back to diagram');
        await user.click(closeButton);
        expect(onClose).toHaveBeenCalled();
      });
    });

    it('hides resize handle on mobile', async () => {
      render(<ChatPanel {...defaultProps} />);

      await waitFor(() => {
        expect(document.querySelector('.resize-handle')).not.toBeInTheDocument();
      });
    });
  });

  describe('Message Scrolling', () => {
    it('scrolls to bottom when new messages arrive', async () => {
      const scrollIntoViewMock = vi.fn();
      window.HTMLElement.prototype.scrollIntoView = scrollIntoViewMock;

      const { rerender } = render(
        <ChatPanel {...defaultProps} messages={[{ role: 'user', content: 'First' }]} />
      );

      rerender(
        <ChatPanel
          {...defaultProps}
          messages={[
            { role: 'user', content: 'First' },
            { role: 'assistant', content: 'Second' },
          ]}
        />
      );

      await waitFor(() => {
        expect(scrollIntoViewMock).toHaveBeenCalled();
      });
    });
  });

  describe('Accessibility', () => {
    it('has accessible form elements', () => {
      render(<ChatPanel {...defaultProps} />);

      expect(screen.getByRole('textbox')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('close button has accessible title', async () => {
      Object.defineProperty(window, 'innerWidth', { value: 768, writable: true });
      fireEvent(window, new Event('resize'));

      render(<ChatPanel {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByTitle('Back to diagram')).toBeInTheDocument();
      });
    });
  });
});

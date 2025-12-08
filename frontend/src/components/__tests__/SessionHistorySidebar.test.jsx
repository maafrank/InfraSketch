/**
 * SessionHistorySidebar Component Tests
 * Tests for the left sidebar session management
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SessionHistorySidebar from '../SessionHistorySidebar';

// Mock the CSS import
vi.mock('../SessionHistorySidebar.css', () => ({}));

// Mock API client
vi.mock('../../api/client', () => ({
  getUserSessions: vi.fn(() =>
    Promise.resolve({
      sessions: [
        {
          session_id: 'session-1',
          name: 'E-commerce Platform',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          node_count: 5,
          edge_count: 4,
          model: 'claude-haiku-4-5',
          has_design_doc: true,
        },
        {
          session_id: 'session-2',
          name: 'Chat Application',
          created_at: new Date(Date.now() - 86400000).toISOString(), // Yesterday
          updated_at: new Date(Date.now() - 86400000).toISOString(),
          node_count: 8,
          edge_count: 7,
          model: 'claude-sonnet-4-5',
          has_design_doc: false,
        },
        {
          session_id: 'session-3',
          name: 'Old Project',
          created_at: new Date(Date.now() - 7 * 86400000).toISOString(), // 7 days ago
          updated_at: new Date(Date.now() - 7 * 86400000).toISOString(),
          node_count: 3,
          edge_count: 2,
          model: 'claude-haiku-4-5',
          has_design_doc: false,
        },
      ],
    })
  ),
  renameSession: vi.fn(() => Promise.resolve({ success: true, name: 'Renamed Session' })),
  deleteSession: vi.fn(() => Promise.resolve({ success: true })),
}));

describe('SessionHistorySidebar', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSessionSelect: vi.fn(),
    onWidthChange: vi.fn(),
    currentSessionId: null,
    sessionNameUpdated: null,
    onSessionDeleted: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, 'alert').mockImplementation(() => {});
    vi.spyOn(window, 'confirm').mockImplementation(() => true);

    // Reset viewport width
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    });
  });

  describe('Visibility', () => {
    it('returns null when isOpen=false', () => {
      const { container } = render(<SessionHistorySidebar {...defaultProps} isOpen={false} />);

      expect(container.firstChild).toBeNull();
    });

    it('renders sidebar when isOpen=true', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(document.querySelector('.session-history-sidebar')).toBeInTheDocument();
      });
    });
  });

  describe('Basic Rendering', () => {
    it('renders header "My Diagrams"', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('My Diagrams');
    });

    it('renders close button', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      expect(screen.getByLabelText('Close session history')).toBeInTheDocument();
    });

    it('close button calls onClose', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      render(<SessionHistorySidebar {...defaultProps} onClose={onClose} />);

      await user.click(screen.getByLabelText('Close session history'));

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Loading State', () => {
    it('shows spinner during loading', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      // Initially shows loading
      expect(document.querySelector('.session-spinner')).toBeInTheDocument();
    });

    it('shows "Loading diagrams..." text', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      expect(screen.getByText('Loading diagrams...')).toBeInTheDocument();
    });

    it('calls getUserSessions on open', async () => {
      const { getUserSessions } = await import('../../api/client');
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(getUserSessions).toHaveBeenCalled();
      });
    });
  });

  describe('Session List', () => {
    it('renders session items from API', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
        expect(screen.getByText('Chat Application')).toBeInTheDocument();
      });
    });

    it('displays session name', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });
    });

    it('displays node count', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('5 nodes')).toBeInTheDocument();
        expect(screen.getByText('8 nodes')).toBeInTheDocument();
      });
    });

    it('displays edge count', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('4 edges')).toBeInTheDocument();
        expect(screen.getByText('7 edges')).toBeInTheDocument();
      });
    });

    it('displays model name (Haiku/Sonnet)', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        // Multiple sessions can have Haiku model, so use getAllByText
        const haikuElements = screen.getAllByText('Haiku');
        expect(haikuElements.length).toBeGreaterThan(0);
        expect(screen.getByText('Sonnet')).toBeInTheDocument();
      });
    });

    it('displays relative date (Today, Yesterday)', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('Today')).toBeInTheDocument();
        expect(screen.getByText('Yesterday')).toBeInTheDocument();
      });
    });

    it('shows doc badge when has_design_doc=true', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        const docBadges = document.querySelectorAll('.doc-badge');
        expect(docBadges.length).toBe(1);
      });
    });

    it('highlights current session with active class', async () => {
      render(<SessionHistorySidebar {...defaultProps} currentSessionId="session-1" />);

      await waitFor(() => {
        const activeItem = document.querySelector('.session-list-item.active');
        expect(activeItem).toBeInTheDocument();
      });
    });
  });

  describe('Session Selection', () => {
    it('calls onSessionSelect with session_id on click', async () => {
      const user = userEvent.setup();
      const onSessionSelect = vi.fn();
      render(<SessionHistorySidebar {...defaultProps} onSessionSelect={onSessionSelect} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      await user.click(screen.getByText('E-commerce Platform'));

      expect(onSessionSelect).toHaveBeenCalledWith('session-1');
    });

    it('closes sidebar on mobile after selection', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      const onSessionSelect = vi.fn();

      // Set mobile viewport
      Object.defineProperty(window, 'innerWidth', { value: 768, writable: true });
      fireEvent(window, new Event('resize'));

      render(
        <SessionHistorySidebar
          {...defaultProps}
          onClose={onClose}
          onSessionSelect={onSessionSelect}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      await user.click(screen.getByText('E-commerce Platform'));

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Context Menu', () => {
    it('shows context menu on right-click', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await waitFor(() => {
        expect(document.querySelector('.session-context-menu')).toBeInTheDocument();
      });
    });

    it('menu has Rename option', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await waitFor(() => {
        expect(screen.getByText('Rename')).toBeInTheDocument();
      });
    });

    it('menu has Delete option', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument();
      });
    });

    it('menu closes on outside click', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await waitFor(() => {
        expect(document.querySelector('.session-context-menu')).toBeInTheDocument();
      });

      // Click outside
      fireEvent.click(document.body);

      await waitFor(() => {
        expect(document.querySelector('.session-context-menu')).not.toBeInTheDocument();
      });
    });
  });

  describe('Rename', () => {
    it('shows input on rename click', async () => {
      const user = userEvent.setup();
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await waitFor(() => {
        expect(screen.getByText('Rename')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Rename'));

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toBeInTheDocument();
      });
    });

    it('populates input with current name', async () => {
      const user = userEvent.setup();
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await user.click(screen.getByText('Rename'));

      await waitFor(() => {
        expect(screen.getByRole('textbox')).toHaveValue('E-commerce Platform');
      });
    });

    it('calls renameSession API on blur', async () => {
      const user = userEvent.setup();
      const { renameSession } = await import('../../api/client');

      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await user.click(screen.getByText('Rename'));

      const input = screen.getByRole('textbox');
      await user.clear(input);
      await user.type(input, 'New Name');

      fireEvent.blur(input);

      await waitFor(() => {
        expect(renameSession).toHaveBeenCalledWith('session-1', 'New Name');
      });
    });

    it('calls renameSession API on Enter', async () => {
      const user = userEvent.setup();
      const { renameSession } = await import('../../api/client');

      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await user.click(screen.getByText('Rename'));

      const input = screen.getByRole('textbox');
      await user.clear(input);
      await user.type(input, 'New Name{Enter}');

      await waitFor(() => {
        expect(renameSession).toHaveBeenCalledWith('session-1', 'New Name');
      });
    });

    it('cancels rename on Escape', async () => {
      const user = userEvent.setup();
      const { renameSession } = await import('../../api/client');

      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await user.click(screen.getByText('Rename'));

      const input = screen.getByRole('textbox');
      await user.clear(input);
      await user.type(input, 'New Name{Escape}');

      // Should not call rename API
      expect(renameSession).not.toHaveBeenCalled();

      // Input should be gone
      await waitFor(() => {
        expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
      });
    });

    it('reloads sessions after rename', async () => {
      const user = userEvent.setup();
      const { getUserSessions } = await import('../../api/client');

      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const initialCallCount = getUserSessions.mock.calls.length;

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await user.click(screen.getByText('Rename'));

      const input = screen.getByRole('textbox');
      await user.type(input, '{Enter}');

      await waitFor(() => {
        expect(getUserSessions.mock.calls.length).toBeGreaterThan(initialCallCount);
      });
    });
  });

  describe('Delete', () => {
    it('shows confirmation dialog', async () => {
      const user = userEvent.setup();
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await user.click(screen.getByText('Delete'));

      expect(window.confirm).toHaveBeenCalledWith(
        'Are you sure you want to delete this session?'
      );
    });

    it('calls deleteSession API on confirm', async () => {
      const user = userEvent.setup();
      const { deleteSession } = await import('../../api/client');

      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await user.click(screen.getByText('Delete'));

      await waitFor(() => {
        expect(deleteSession).toHaveBeenCalledWith('session-1');
      });
    });

    it('does not delete if user cancels', async () => {
      const user = userEvent.setup();
      const { deleteSession } = await import('../../api/client');
      window.confirm.mockReturnValue(false);

      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await user.click(screen.getByText('Delete'));

      expect(deleteSession).not.toHaveBeenCalled();
    });

    it('reloads sessions after delete', async () => {
      const user = userEvent.setup();
      const { getUserSessions } = await import('../../api/client');

      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const initialCallCount = getUserSessions.mock.calls.length;

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await user.click(screen.getByText('Delete'));

      await waitFor(() => {
        expect(getUserSessions.mock.calls.length).toBeGreaterThan(initialCallCount);
      });
    });

    it('calls onSessionDeleted if deleting current session', async () => {
      const user = userEvent.setup();
      const onSessionDeleted = vi.fn();

      render(
        <SessionHistorySidebar
          {...defaultProps}
          currentSessionId="session-1"
          onSessionDeleted={onSessionDeleted}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('E-commerce Platform')).toBeInTheDocument();
      });

      const sessionItem = screen.getByText('E-commerce Platform').closest('.session-list-item');
      fireEvent.contextMenu(sessionItem);

      await user.click(screen.getByText('Delete'));

      await waitFor(() => {
        expect(onSessionDeleted).toHaveBeenCalledWith('session-1');
      });
    });
  });

  describe('Empty State', () => {
    it('shows empty message when no sessions', async () => {
      const { getUserSessions } = await import('../../api/client');
      getUserSessions.mockResolvedValue({ sessions: [] });

      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('No diagrams yet')).toBeInTheDocument();
      });
    });

    it('shows suggestion to create first diagram', async () => {
      const { getUserSessions } = await import('../../api/client');
      getUserSessions.mockResolvedValue({ sessions: [] });

      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(
          screen.getByText('Create your first diagram to get started!')
        ).toBeInTheDocument();
      });
    });
  });

  describe('Error State', () => {
    it('shows error message on load failure', async () => {
      const { getUserSessions } = await import('../../api/client');
      getUserSessions.mockRejectedValue(new Error('Network error'));

      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load sessions')).toBeInTheDocument();
      });
    });

    it('shows retry button', async () => {
      const { getUserSessions } = await import('../../api/client');
      getUserSessions.mockRejectedValue(new Error('Network error'));

      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
    });

    it('retry button reloads sessions', async () => {
      const user = userEvent.setup();
      const { getUserSessions } = await import('../../api/client');

      // First call fails
      getUserSessions.mockRejectedValueOnce(new Error('Network error'));
      // Second call succeeds
      getUserSessions.mockResolvedValue({ sessions: [] });

      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Retry'));

      await waitFor(() => {
        expect(getUserSessions).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Resize (Desktop)', () => {
    it('renders resize handle on desktop', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(document.querySelector('.resize-handle-right')).toBeInTheDocument();
      });
    });

    it('has default width of 300px', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        const sidebar = document.querySelector('.session-history-sidebar');
        expect(sidebar).toHaveStyle({ width: '300px' });
      });
    });

    it('notifies parent via onWidthChange', async () => {
      const onWidthChange = vi.fn();
      render(<SessionHistorySidebar {...defaultProps} onWidthChange={onWidthChange} />);

      await waitFor(() => {
        expect(onWidthChange).toHaveBeenCalled();
      });
    });
  });

  describe('Mobile Mode', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 768,
      });
      fireEvent(window, new Event('resize'));
    });

    it('adds mobile-modal class at ≤768px', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        const sidebar = document.querySelector('.session-history-sidebar');
        expect(sidebar).toHaveClass('mobile-modal');
      });
    });

    it('sets width to 100%', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        const sidebar = document.querySelector('.session-history-sidebar');
        expect(sidebar).toHaveStyle({ width: '100%' });
      });
    });

    it('hides resize handle on mobile', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        expect(document.querySelector('.resize-handle-right')).not.toBeInTheDocument();
      });
    });
  });

  describe('Session Name Update Refresh', () => {
    it('reloads sessions when sessionNameUpdated changes', async () => {
      const { getUserSessions } = await import('../../api/client');

      // Reset mock to return valid sessions
      getUserSessions.mockResolvedValue({
        sessions: [
          {
            session_id: 'session-1',
            name: 'Test Session',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            node_count: 5,
            edge_count: 4,
            model: 'claude-haiku-4-5',
            has_design_doc: false,
          },
        ],
      });

      const { rerender } = render(
        <SessionHistorySidebar {...defaultProps} currentSessionId="session-1" />
      );

      // Wait for sessions to load
      await waitFor(() => {
        expect(document.querySelector('.session-list-item')).toBeInTheDocument();
      });

      const initialCallCount = getUserSessions.mock.calls.length;

      // Simulate session name update
      rerender(
        <SessionHistorySidebar
          {...defaultProps}
          currentSessionId="session-1"
          sessionNameUpdated={Date.now()}
        />
      );

      await waitFor(() => {
        expect(getUserSessions.mock.calls.length).toBeGreaterThan(initialCallCount);
      });
    });
  });

  describe('Date Formatting', () => {
    beforeEach(async () => {
      // Reset mock to return sessions with different dates
      const { getUserSessions } = await import('../../api/client');
      getUserSessions.mockResolvedValue({
        sessions: [
          {
            session_id: 'session-today',
            name: 'Today Session',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            node_count: 5,
            edge_count: 4,
            model: 'claude-haiku-4-5',
            has_design_doc: false,
          },
          {
            session_id: 'session-yesterday',
            name: 'Yesterday Session',
            created_at: new Date(Date.now() - 86400000).toISOString(), // Yesterday
            updated_at: new Date(Date.now() - 86400000).toISOString(),
            node_count: 3,
            edge_count: 2,
            model: 'claude-haiku-4-5',
            has_design_doc: false,
          },
          {
            session_id: 'session-days-ago',
            name: 'Days Ago Session',
            created_at: new Date(Date.now() - 5 * 86400000).toISOString(), // 5 days ago (within "X days ago" range)
            updated_at: new Date(Date.now() - 5 * 86400000).toISOString(),
            node_count: 2,
            edge_count: 1,
            model: 'claude-haiku-4-5',
            has_design_doc: false,
          },
        ],
      });
    });

    it('shows "Today" for today\'s sessions', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        // First session has today's date
        const dateElements = document.querySelectorAll('.session-date-compact');
        expect(dateElements.length).toBeGreaterThan(0);
        const todayElement = Array.from(dateElements).find((el) => el.textContent === 'Today');
        expect(todayElement).toBeTruthy();
      });
    });

    it('shows "Yesterday" for yesterday\'s sessions', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        // Second session has yesterday's date
        const dateElements = document.querySelectorAll('.session-date-compact');
        const yesterdayElement = Array.from(dateElements).find(
          (el) => el.textContent === 'Yesterday'
        );
        expect(yesterdayElement).toBeTruthy();
      });
    });

    it('shows "X days ago" for older sessions', async () => {
      render(<SessionHistorySidebar {...defaultProps} />);

      await waitFor(() => {
        // Third session has 7 days ago date
        const dateElements = document.querySelectorAll('.session-date-compact');
        const olderElement = Array.from(dateElements).find((el) =>
          el.textContent.includes('days ago')
        );
        expect(olderElement).toBeTruthy();
      });
    });
  });
});

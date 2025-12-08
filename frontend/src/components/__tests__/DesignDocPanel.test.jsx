/**
 * DesignDocPanel Component Tests
 * Tests for the design document editor panel with TipTap
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DesignDocPanel from '../DesignDocPanel';

// Mock TipTap
const mockEditor = {
  chain: vi.fn(() => ({
    focus: vi.fn(() => ({
      toggleBold: vi.fn(() => ({ run: vi.fn() })),
      toggleItalic: vi.fn(() => ({ run: vi.fn() })),
      toggleHeading: vi.fn(() => ({ run: vi.fn() })),
      toggleBulletList: vi.fn(() => ({ run: vi.fn() })),
      toggleOrderedList: vi.fn(() => ({ run: vi.fn() })),
    })),
  })),
  isActive: vi.fn(() => false),
  getHTML: vi.fn(() => '<p>Test content</p>'),
  commands: {
    setContent: vi.fn(),
  },
};

vi.mock('@tiptap/react', () => ({
  useEditor: vi.fn(() => mockEditor),
  EditorContent: ({ editor }) => (
    <div data-testid="tiptap-editor">{editor ? 'Editor Content' : 'No Editor'}</div>
  ),
}));

vi.mock('@tiptap/starter-kit', () => ({
  default: {},
}));

// Mock marked
vi.mock('marked', () => ({
  marked: {
    setOptions: vi.fn(),
    parse: vi.fn((content) => `<p>${content}</p>`),
  },
}));

// Mock turndown
vi.mock('turndown', () => ({
  default: vi.fn().mockImplementation(() => ({
    turndown: vi.fn((html) => html.replace(/<[^>]*>/g, '')),
  })),
}));

// Mock html-to-image
vi.mock('html-to-image', () => ({
  toPng: vi.fn(() => Promise.resolve('data:image/png;base64,testImageData')),
}));

describe('DesignDocPanel', () => {
  const defaultProps = {
    designDoc: '# Test Document\n\nThis is test content.',
    onSave: vi.fn(() => Promise.resolve()),
    onClose: vi.fn(),
    onExport: vi.fn(() => Promise.resolve()),
    isGenerating: false,
    onWidthChange: vi.fn(),
    onApplyLayout: vi.fn(),
    sessionHistorySidebarWidth: 0,
  };

  let originalCreateObjectURL;
  let originalRevokeObjectURL;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, 'alert').mockImplementation(() => {});
    vi.useFakeTimers({ shouldAdvanceTime: true });

    // Mock URL APIs
    originalCreateObjectURL = window.URL.createObjectURL;
    originalRevokeObjectURL = window.URL.revokeObjectURL;
    window.URL.createObjectURL = vi.fn(() => 'blob:test-url');
    window.URL.revokeObjectURL = vi.fn();

    // Reset viewport width
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    });

    // Mock document.querySelector for react-flow viewport
    const mockViewport = document.createElement('div');
    mockViewport.className = 'react-flow__viewport';
    document.body.appendChild(mockViewport);
  });

  afterEach(() => {
    vi.useRealTimers();
    window.URL.createObjectURL = originalCreateObjectURL;
    window.URL.revokeObjectURL = originalRevokeObjectURL;

    // Clean up mock viewport
    const viewport = document.querySelector('.react-flow__viewport');
    if (viewport) {
      viewport.remove();
    }
  });

  describe('Basic Rendering', () => {
    it('renders panel with header "Design Document"', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Design Document');
    });

    it('renders close button', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(screen.getByTitle('Close')).toBeInTheDocument();
    });

    it('renders toolbar buttons', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(screen.getByTitle('Bold')).toBeInTheDocument();
      expect(screen.getByTitle('Italic')).toBeInTheDocument();
      expect(screen.getByTitle('Heading 1')).toBeInTheDocument();
      expect(screen.getByTitle('Heading 2')).toBeInTheDocument();
      expect(screen.getByTitle('Bullet List')).toBeInTheDocument();
      expect(screen.getByTitle('Numbered List')).toBeInTheDocument();
    });

    it('renders export dropdown', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('renders save status indicator', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(screen.getByText('✓ Saved')).toBeInTheDocument();
    });

    it('renders TipTap editor', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(screen.getByTestId('tiptap-editor')).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('shows generating overlay when isGenerating=true', () => {
      render(<DesignDocPanel {...defaultProps} isGenerating={true} />);

      expect(screen.getByText('Generating Design Document...')).toBeInTheDocument();
    });

    it('hides overlay when isGenerating=false', () => {
      render(<DesignDocPanel {...defaultProps} isGenerating={false} />);

      expect(screen.queryByText('Generating Design Document...')).not.toBeInTheDocument();
    });

    it('displays loading message during generation', () => {
      render(<DesignDocPanel {...defaultProps} isGenerating={true} />);

      expect(
        screen.getByText(/This may take 1-2 minutes/)
      ).toBeInTheDocument();
    });

    it('shows spinner during generation', () => {
      render(<DesignDocPanel {...defaultProps} isGenerating={true} />);

      expect(document.querySelector('.generating-spinner')).toBeInTheDocument();
    });
  });

  describe('Editor Functionality', () => {
    it('renders TipTap editor component', () => {
      render(<DesignDocPanel {...defaultProps} />);

      // Verify the TipTap editor is rendered via our mock
      expect(screen.getByTestId('tiptap-editor')).toBeInTheDocument();
    });

    it('renders editor content area', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(screen.getByTestId('tiptap-editor')).toHaveTextContent('Editor Content');
    });
  });

  describe('Toolbar Actions', () => {
    it('Bold button triggers editor command', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<DesignDocPanel {...defaultProps} />);

      await user.click(screen.getByTitle('Bold'));

      expect(mockEditor.chain).toHaveBeenCalled();
    });

    it('Italic button triggers editor command', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<DesignDocPanel {...defaultProps} />);

      await user.click(screen.getByTitle('Italic'));

      expect(mockEditor.chain).toHaveBeenCalled();
    });

    it('H1 button triggers editor command', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<DesignDocPanel {...defaultProps} />);

      await user.click(screen.getByTitle('Heading 1'));

      expect(mockEditor.chain).toHaveBeenCalled();
    });

    it('H2 button triggers editor command', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<DesignDocPanel {...defaultProps} />);

      await user.click(screen.getByTitle('Heading 2'));

      expect(mockEditor.chain).toHaveBeenCalled();
    });

    it('Bullet List button triggers editor command', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<DesignDocPanel {...defaultProps} />);

      await user.click(screen.getByTitle('Bullet List'));

      expect(mockEditor.chain).toHaveBeenCalled();
    });

    it('Numbered List button triggers editor command', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<DesignDocPanel {...defaultProps} />);

      await user.click(screen.getByTitle('Numbered List'));

      expect(mockEditor.chain).toHaveBeenCalled();
    });
  });

  describe('Save Status', () => {
    it('shows "✓ Saved" initially', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(screen.getByText('✓ Saved')).toBeInTheDocument();
    });

    it('has correct class for saved status', () => {
      render(<DesignDocPanel {...defaultProps} />);

      const statusElement = document.querySelector('.save-status.saved');
      expect(statusElement).toBeInTheDocument();
    });
  });

  describe('Export Functionality', () => {
    it('dropdown shows all export options', () => {
      render(<DesignDocPanel {...defaultProps} />);

      const select = screen.getByRole('combobox');
      const options = select.querySelectorAll('option');

      expect(options).toHaveLength(4); // Default + 3 export options
      expect(screen.getByText('📕 PDF')).toBeInTheDocument();
      expect(screen.getByText('📝 Markdown')).toBeInTheDocument();
      expect(screen.getByText('🖼️ PNG')).toBeInTheDocument();
    });

    it('calls handleExport when format selected', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<DesignDocPanel {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'pdf');

      // Export should be triggered
      await vi.advanceTimersByTimeAsync(600);
    });

    it('resets dropdown after selection', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<DesignDocPanel {...defaultProps} />);

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'pdf');

      // Dropdown should reset to default
      await vi.advanceTimersByTimeAsync(600);
      expect(select).toHaveValue('');
    });
  });

  describe('Close Button', () => {
    it('calls onClose when clicked', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      const onClose = vi.fn();
      render(<DesignDocPanel {...defaultProps} onClose={onClose} />);

      await user.click(screen.getByTitle('Close'));

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Resize (Desktop)', () => {
    it('renders resize handle on desktop', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(document.querySelector('.resize-handle-right')).toBeInTheDocument();
    });

    it('has default width of 400px', () => {
      render(<DesignDocPanel {...defaultProps} />);

      const panel = document.querySelector('.design-doc-panel');
      expect(panel).toHaveStyle({ width: '400px' });
    });

    it('respects sessionHistorySidebarWidth for left offset', () => {
      render(<DesignDocPanel {...defaultProps} sessionHistorySidebarWidth={300} />);

      const panel = document.querySelector('.design-doc-panel');
      expect(panel).toHaveStyle({ left: '300px' });
    });

    it('notifies parent via onWidthChange', async () => {
      const onWidthChange = vi.fn();
      render(<DesignDocPanel {...defaultProps} onWidthChange={onWidthChange} />);

      await vi.advanceTimersByTimeAsync(20);

      expect(onWidthChange).toHaveBeenCalled();
    });

    it('starts resizing on mousedown', () => {
      render(<DesignDocPanel {...defaultProps} />);

      const resizeHandle = document.querySelector('.resize-handle-right');
      fireEvent.mouseDown(resizeHandle);

      // Verify document body style is set for resize
      expect(document.body.style.userSelect).toBe('none');
    });

    it('stops resizing on mouseup', () => {
      render(<DesignDocPanel {...defaultProps} />);

      const resizeHandle = document.querySelector('.resize-handle-right');
      fireEvent.mouseDown(resizeHandle);
      fireEvent.mouseUp(document);

      expect(document.body.style.userSelect).toBe('');
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
      render(<DesignDocPanel {...defaultProps} />);

      await vi.advanceTimersByTimeAsync(100);

      const panel = document.querySelector('.design-doc-panel');
      expect(panel).toHaveClass('mobile-modal');
    });

    it('hides resize handle on mobile', async () => {
      render(<DesignDocPanel {...defaultProps} />);

      await vi.advanceTimersByTimeAsync(100);

      expect(document.querySelector('.resize-handle-right')).not.toBeInTheDocument();
    });
  });

  describe('CSS Classes', () => {
    it('has design-doc-panel class', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(document.querySelector('.design-doc-panel')).toBeInTheDocument();
    });

    it('has design-doc-header class', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(document.querySelector('.design-doc-header')).toBeInTheDocument();
    });

    it('has design-doc-toolbar class', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(document.querySelector('.design-doc-toolbar')).toBeInTheDocument();
    });

    it('has design-doc-editor class', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(document.querySelector('.design-doc-editor')).toBeInTheDocument();
    });

    it('has design-doc-footer class', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(document.querySelector('.design-doc-footer')).toBeInTheDocument();
    });

    it('has export-dropdown class', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(document.querySelector('.export-dropdown')).toBeInTheDocument();
    });
  });

  describe('Empty Design Doc', () => {
    it('handles null designDoc', () => {
      render(<DesignDocPanel {...defaultProps} designDoc={null} />);

      expect(screen.getByTestId('tiptap-editor')).toBeInTheDocument();
    });

    it('handles empty string designDoc', () => {
      render(<DesignDocPanel {...defaultProps} designDoc="" />);

      expect(screen.getByTestId('tiptap-editor')).toBeInTheDocument();
    });
  });

  describe('Export Button States', () => {
    it('has export-buttons container', () => {
      render(<DesignDocPanel {...defaultProps} />);

      expect(document.querySelector('.export-buttons')).toBeInTheDocument();
    });

    it('dropdown has correct default option', () => {
      render(<DesignDocPanel {...defaultProps} />);

      const defaultOption = screen.getByText('Export ▼');
      expect(defaultOption).toHaveValue('');
    });
  });

  describe('Panel Positioning', () => {
    it('sets left position based on sessionHistorySidebarWidth', () => {
      render(<DesignDocPanel {...defaultProps} sessionHistorySidebarWidth={250} />);

      const panel = document.querySelector('.design-doc-panel');
      expect(panel).toHaveStyle({ left: '250px' });
    });

    it('sets left to 0 when sessionHistorySidebarWidth is 0', () => {
      render(<DesignDocPanel {...defaultProps} sessionHistorySidebarWidth={0} />);

      const panel = document.querySelector('.design-doc-panel');
      expect(panel).toHaveStyle({ left: '0px' });
    });
  });
});

/**
 * ExportButton Component Tests
 * Tests for the export dropdown with PNG/PDF/Markdown options
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ExportButton from '../ExportButton';

// Mock html-to-image
vi.mock('html-to-image', () => ({
  toPng: vi.fn(() => Promise.resolve('data:image/png;base64,testImageData')),
}));

// Mock API client
vi.mock('../../api/client', () => ({
  exportDesignDoc: vi.fn(() =>
    Promise.resolve({
      pdf: {
        content: 'base64PdfContent',
        filename: 'design-document.pdf',
      },
      markdown: {
        content: '# Design Document',
        filename: 'design-document.md',
      },
      diagram_png: {
        content: 'base64PngContent',
        filename: 'diagram.png',
      },
    })
  ),
}));

describe('ExportButton', () => {
  const mockReactFlowInstance = {
    getNodes: vi.fn(() => [
      { id: 'node-1', position: { x: 100, y: 100 }, width: 200, height: 100 },
      { id: 'node-2', position: { x: 400, y: 200 }, width: 200, height: 100 },
    ]),
    getViewport: vi.fn(() => ({ x: 0, y: 0, zoom: 1 })),
    setViewport: vi.fn(),
  };

  const defaultProps = {
    sessionId: 'test-session-123',
    reactFlowInstance: mockReactFlowInstance,
  };

  let originalCreateObjectURL;
  let originalRevokeObjectURL;
  let appendedElements = [];
  let clickedLinks = [];

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock window.alert
    vi.spyOn(window, 'alert').mockImplementation(() => {});

    // Mock URL.createObjectURL and revokeObjectURL
    originalCreateObjectURL = window.URL.createObjectURL;
    originalRevokeObjectURL = window.URL.revokeObjectURL;
    window.URL.createObjectURL = vi.fn(() => 'blob:test-url');
    window.URL.revokeObjectURL = vi.fn();

    // Track appended elements and clicks
    appendedElements = [];
    clickedLinks = [];
    const originalAppendChild = document.body.appendChild.bind(document.body);
    const originalRemoveChild = document.body.removeChild.bind(document.body);

    vi.spyOn(document.body, 'appendChild').mockImplementation((el) => {
      appendedElements.push(el);
      if (el.tagName === 'A') {
        vi.spyOn(el, 'click').mockImplementation(() => {
          clickedLinks.push(el);
        });
      }
      return originalAppendChild(el);
    });

    vi.spyOn(document.body, 'removeChild').mockImplementation((el) => {
      return originalRemoveChild(el);
    });

    // Mock document.querySelector for .react-flow__viewport
    const mockViewport = document.createElement('div');
    mockViewport.className = 'react-flow__viewport';
    document.body.appendChild(mockViewport);
  });

  afterEach(() => {
    window.URL.createObjectURL = originalCreateObjectURL;
    window.URL.revokeObjectURL = originalRevokeObjectURL;

    // Clean up mock viewport
    const viewport = document.querySelector('.react-flow__viewport');
    if (viewport) {
      viewport.remove();
    }
  });

  describe('Basic Rendering', () => {
    it('renders export button', () => {
      render(<ExportButton {...defaultProps} />);

      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('button shows "📄 Export Design Doc"', () => {
      render(<ExportButton {...defaultProps} />);

      expect(screen.getByText('📄 Export Design Doc')).toBeInTheDocument();
    });

    it('has export-button-container class', () => {
      render(<ExportButton {...defaultProps} />);

      expect(document.querySelector('.export-button-container')).toBeInTheDocument();
    });

    it('has export-button class on button', () => {
      render(<ExportButton {...defaultProps} />);

      expect(document.querySelector('.export-button')).toBeInTheDocument();
    });
  });

  describe('Menu Toggle', () => {
    it('menu hidden by default', () => {
      render(<ExportButton {...defaultProps} />);

      expect(document.querySelector('.export-menu')).not.toBeInTheDocument();
    });

    it('shows menu on button click', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));

      expect(document.querySelector('.export-menu')).toBeInTheDocument();
    });

    it('hides menu on second click', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      const button = screen.getByRole('button', { name: /Export Design Doc/i });

      await user.click(button);
      expect(document.querySelector('.export-menu')).toBeInTheDocument();

      await user.click(button);
      expect(document.querySelector('.export-menu')).not.toBeInTheDocument();
    });
  });

  describe('Export Options', () => {
    it('menu shows PNG option', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));

      expect(screen.getByText('🖼️ Export as PNG')).toBeInTheDocument();
    });

    it('menu shows PDF option', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));

      expect(screen.getByText('📕 Export as PDF')).toBeInTheDocument();
    });

    it('menu shows Markdown option', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));

      expect(screen.getByText('📝 Export as Markdown')).toBeInTheDocument();
    });

    it('menu shows "PDF + Markdown" option', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));

      expect(screen.getByText('📦 Export PDF + Markdown')).toBeInTheDocument();
    });

    it('renders 4 export options total', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));

      const menuButtons = document.querySelectorAll('.export-menu button');
      expect(menuButtons).toHaveLength(4);
    });
  });

  describe('Export Actions', () => {
    it('PNG export captures diagram and downloads directly', async () => {
      const user = userEvent.setup();
      const { toPng } = await import('html-to-image');

      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('🖼️ Export as PNG'));

      await waitFor(() => {
        expect(toPng).toHaveBeenCalled();
      });
    });

    it('PDF export calls exportDesignDoc API', async () => {
      const user = userEvent.setup();
      const { exportDesignDoc } = await import('../../api/client');

      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📕 Export as PDF'));

      await waitFor(() => {
        expect(exportDesignDoc).toHaveBeenCalledWith(
          'test-session-123',
          'pdf',
          expect.any(String)
        );
      });
    });

    it('Markdown export calls exportDesignDoc API', async () => {
      const user = userEvent.setup();
      const { exportDesignDoc } = await import('../../api/client');

      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📝 Export as Markdown'));

      await waitFor(() => {
        expect(exportDesignDoc).toHaveBeenCalledWith(
          'test-session-123',
          'markdown',
          expect.any(String)
        );
      });
    });

    it('Both export calls exportDesignDoc with "both" format', async () => {
      const user = userEvent.setup();
      const { exportDesignDoc } = await import('../../api/client');

      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📦 Export PDF + Markdown'));

      await waitFor(() => {
        expect(exportDesignDoc).toHaveBeenCalledWith(
          'test-session-123',
          'both',
          expect.any(String)
        );
      });
    });
  });

  describe('Loading State', () => {
    it('disables button during export', async () => {
      const user = userEvent.setup();
      // Make the export take longer
      const { exportDesignDoc } = await import('../../api/client');
      exportDesignDoc.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📕 Export as PDF'));

      // Button should be disabled while loading
      await waitFor(() => {
        expect(screen.getByRole('button')).toBeDisabled();
      });
    });

    it('shows "Generating..." text during export', async () => {
      const user = userEvent.setup();
      const { exportDesignDoc } = await import('../../api/client');

      // Create a deferred promise we can resolve later
      let resolveExportFn;
      const exportPromise = new Promise((resolve) => {
        resolveExportFn = resolve;
      });
      exportDesignDoc.mockReturnValue(exportPromise);

      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📕 Export as PDF'));

      await waitFor(() => {
        expect(screen.getByText('Generating...')).toBeInTheDocument();
      });

      // Cleanup - resolve the promise
      resolveExportFn({ pdf: { content: 'test', filename: 'test.pdf' } });
    });

    it('hides menu during export', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      expect(document.querySelector('.export-menu')).toBeInTheDocument();

      await user.click(screen.getByText('📕 Export as PDF'));

      // Menu should close immediately when export starts
      await waitFor(() => {
        expect(document.querySelector('.export-menu')).not.toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('shows alert when no session', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} sessionId={null} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📕 Export as PDF'));

      expect(window.alert).toHaveBeenCalledWith('No active session to export');
    });

    it('shows alert when diagram capture fails', async () => {
      const user = userEvent.setup();

      // Make getNodes return empty array
      const emptyReactFlowInstance = {
        ...mockReactFlowInstance,
        getNodes: vi.fn(() => []),
      };

      render(<ExportButton {...defaultProps} reactFlowInstance={emptyReactFlowInstance} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📕 Export as PDF'));

      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith(
          'Failed to capture diagram. Please try again.'
        );
      });
    });

    it('shows alert when export API fails', async () => {
      const user = userEvent.setup();
      const { exportDesignDoc } = await import('../../api/client');
      exportDesignDoc.mockRejectedValue(new Error('API Error'));

      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📕 Export as PDF'));

      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith(
          'Failed to generate design document. Please try again.'
        );
      });
    });

    it('shows alert when reactFlowInstance is not available', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} reactFlowInstance={null} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📕 Export as PDF'));

      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith(
          'Failed to capture diagram. Please try again.'
        );
      });
    });
  });

  describe('Diagram Capture', () => {
    it('calculates bounding box from nodes', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('🖼️ Export as PNG'));

      // The component calls getNodes to calculate bounding box
      await waitFor(() => {
        expect(mockReactFlowInstance.getNodes).toHaveBeenCalled();
      });
    });

    it('sets viewport before capture', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('🖼️ Export as PNG'));

      await waitFor(() => {
        expect(mockReactFlowInstance.setViewport).toHaveBeenCalled();
      });
    });

    it('restores original viewport after capture', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('🖼️ Export as PNG'));

      await waitFor(() => {
        // setViewport should be called twice: once to set, once to restore
        expect(mockReactFlowInstance.setViewport.mock.calls.length).toBeGreaterThanOrEqual(2);
      });
    });

    it('stores original viewport before changing', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('🖼️ Export as PNG'));

      await waitFor(() => {
        expect(mockReactFlowInstance.getViewport).toHaveBeenCalled();
      });
    });
  });

  describe('File Downloads', () => {
    it('handles PDF export response with download', async () => {
      const user = userEvent.setup();
      const { exportDesignDoc } = await import('../../api/client');

      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📕 Export as PDF'));

      // The export should be called and complete
      await waitFor(() => {
        expect(exportDesignDoc).toHaveBeenCalled();
      });
    });

    it('handles Markdown export response with download', async () => {
      const user = userEvent.setup();
      const { exportDesignDoc } = await import('../../api/client');

      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📝 Export as Markdown'));

      await waitFor(() => {
        expect(exportDesignDoc).toHaveBeenCalledWith(
          'test-session-123',
          'markdown',
          expect.any(String)
        );
      });
    });

    it('handles Both export response with downloads', async () => {
      const user = userEvent.setup();
      const { exportDesignDoc } = await import('../../api/client');

      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📦 Export PDF + Markdown'));

      await waitFor(() => {
        expect(exportDesignDoc).toHaveBeenCalledWith(
          'test-session-123',
          'both',
          expect.any(String)
        );
      });
    });
  });

  describe('Button State After Export', () => {
    it('re-enables button after successful export', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📕 Export as PDF'));

      await waitFor(() => {
        expect(screen.getByRole('button')).not.toBeDisabled();
      });
    });

    it('shows original text after successful export', async () => {
      const user = userEvent.setup();
      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📕 Export as PDF'));

      await waitFor(() => {
        expect(screen.getByText('📄 Export Design Doc')).toBeInTheDocument();
      });
    });

    it('re-enables button after failed export', async () => {
      const user = userEvent.setup();
      const { exportDesignDoc } = await import('../../api/client');
      exportDesignDoc.mockRejectedValue(new Error('Failed'));

      render(<ExportButton {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: /Export Design Doc/i }));
      await user.click(screen.getByText('📕 Export as PDF'));

      await waitFor(() => {
        expect(screen.getByRole('button')).not.toBeDisabled();
      });
    });
  });
});

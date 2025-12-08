/**
 * AddNodeModal Component Tests
 * Tests for the manual node creation modal
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AddNodeModal from '../AddNodeModal';

// Mock the CSS import
vi.mock('../AddNodeModal.css', () => ({}));

describe('AddNodeModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onAdd: vi.fn(),
    preSelectedType: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.alert
    vi.spyOn(window, 'alert').mockImplementation(() => {});
  });

  describe('Modal Visibility', () => {
    it('returns null when isOpen=false', () => {
      const { container } = render(<AddNodeModal {...defaultProps} isOpen={false} />);

      expect(container.firstChild).toBeNull();
    });

    it('renders modal when isOpen=true', () => {
      render(<AddNodeModal {...defaultProps} />);

      expect(screen.getByText('Add New Node')).toBeInTheDocument();
    });

    it('closes on overlay click', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      render(<AddNodeModal {...defaultProps} onClose={onClose} />);

      // Click on the overlay (modal-overlay class)
      const overlay = document.querySelector('.modal-overlay');
      await user.click(overlay);

      expect(onClose).toHaveBeenCalled();
    });

    it('does not close when clicking modal content', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      render(<AddNodeModal {...defaultProps} onClose={onClose} />);

      // Click on the modal content (not overlay)
      const content = document.querySelector('.modal-content');
      await user.click(content);

      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe('Form Fields', () => {
    it('renders type dropdown with all 10 node types', () => {
      render(<AddNodeModal {...defaultProps} />);

      const select = screen.getByLabelText('Type *');
      const options = select.querySelectorAll('option');

      expect(options).toHaveLength(10);
    });

    it('renders all node type options', () => {
      render(<AddNodeModal {...defaultProps} />);

      expect(screen.getByRole('option', { name: 'API' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Database' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Cache' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Server' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Load Balancer' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Queue' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'CDN' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Gateway' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Storage' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Service' })).toBeInTheDocument();
    });

    it('renders label input (required)', () => {
      render(<AddNodeModal {...defaultProps} />);

      const labelInput = screen.getByLabelText('Label *');
      expect(labelInput).toBeInTheDocument();
      expect(labelInput).toHaveAttribute('required');
    });

    it('renders description textarea', () => {
      render(<AddNodeModal {...defaultProps} />);

      expect(screen.getByLabelText('Description')).toBeInTheDocument();
    });

    it('renders technology input', () => {
      render(<AddNodeModal {...defaultProps} />);

      expect(screen.getByLabelText('Technology')).toBeInTheDocument();
    });

    it('renders notes textarea', () => {
      render(<AddNodeModal {...defaultProps} />);

      expect(screen.getByLabelText('Notes')).toBeInTheDocument();
    });
  });

  describe('Pre-selected Type', () => {
    it('sets type dropdown to preSelectedType', () => {
      render(<AddNodeModal {...defaultProps} preSelectedType="database" />);

      const select = screen.getByLabelText('Type *');
      expect(select).toHaveValue('database');
    });

    it('updates type when preSelectedType prop changes', async () => {
      const { rerender } = render(<AddNodeModal {...defaultProps} preSelectedType="api" />);

      expect(screen.getByLabelText('Type *')).toHaveValue('api');

      rerender(<AddNodeModal {...defaultProps} preSelectedType="cache" />);

      await waitFor(() => {
        expect(screen.getByLabelText('Type *')).toHaveValue('cache');
      });
    });

    it('defaults to api when no preSelectedType', () => {
      render(<AddNodeModal {...defaultProps} />);

      const select = screen.getByLabelText('Type *');
      expect(select).toHaveValue('api');
    });
  });

  describe('Form Validation', () => {
    it('shows alert when label is whitespace only', async () => {
      const user = userEvent.setup();
      render(<AddNodeModal {...defaultProps} />);

      // Type whitespace in the label field
      const labelInput = screen.getByLabelText('Label *');
      await user.type(labelInput, '   ');

      // Try to submit
      const submitButton = screen.getByRole('button', { name: 'Add Node' });
      await user.click(submitButton);

      expect(window.alert).toHaveBeenCalledWith('Please enter a node label');
    });

    it('prevents submission without label', async () => {
      const user = userEvent.setup();
      const onAdd = vi.fn();
      render(<AddNodeModal {...defaultProps} onAdd={onAdd} />);

      // HTML5 required attribute prevents submission with empty field
      // The form won't submit, so onAdd won't be called
      const submitButton = screen.getByRole('button', { name: 'Add Node' });
      await user.click(submitButton);

      expect(onAdd).not.toHaveBeenCalled();
    });

    it('label input has required attribute', () => {
      render(<AddNodeModal {...defaultProps} />);

      const labelInput = screen.getByLabelText('Label *');
      expect(labelInput).toHaveAttribute('required');
    });
  });

  describe('Form Submission', () => {
    it('calls onAdd with node object on submit', async () => {
      const user = userEvent.setup();
      const onAdd = vi.fn();
      render(<AddNodeModal {...defaultProps} onAdd={onAdd} />);

      // Fill in the label
      const labelInput = screen.getByLabelText('Label *');
      await user.type(labelInput, 'User Service');

      // Submit
      const submitButton = screen.getByRole('button', { name: 'Add Node' });
      await user.click(submitButton);

      expect(onAdd).toHaveBeenCalledTimes(1);
      const calledNode = onAdd.mock.calls[0][0];
      expect(calledNode.label).toBe('User Service');
      expect(calledNode.type).toBe('api');
    });

    it('generates ID from label (lowercase, hyphenated)', async () => {
      const user = userEvent.setup();
      const onAdd = vi.fn();
      render(<AddNodeModal {...defaultProps} onAdd={onAdd} />);

      const labelInput = screen.getByLabelText('Label *');
      await user.type(labelInput, 'User Auth Service');

      const submitButton = screen.getByRole('button', { name: 'Add Node' });
      await user.click(submitButton);

      const calledNode = onAdd.mock.calls[0][0];
      expect(calledNode.id).toMatch(/^user-auth-service-\d+$/);
    });

    it('includes timestamp in ID for uniqueness', async () => {
      const user = userEvent.setup();
      const onAdd = vi.fn();
      render(<AddNodeModal {...defaultProps} onAdd={onAdd} />);

      const labelInput = screen.getByLabelText('Label *');
      await user.type(labelInput, 'Test Node');

      const submitButton = screen.getByRole('button', { name: 'Add Node' });
      await user.click(submitButton);

      const calledNode = onAdd.mock.calls[0][0];
      // ID should end with a timestamp
      const idParts = calledNode.id.split('-');
      const timestamp = idParts[idParts.length - 1];
      expect(parseInt(timestamp, 10)).toBeGreaterThan(0);
    });

    it('includes all form fields in node object', async () => {
      const user = userEvent.setup();
      const onAdd = vi.fn();
      render(<AddNodeModal {...defaultProps} onAdd={onAdd} />);

      // Fill all fields
      await user.selectOptions(screen.getByLabelText('Type *'), 'database');
      await user.type(screen.getByLabelText('Label *'), 'PostgreSQL DB');
      await user.type(screen.getByLabelText('Description'), 'Main database');
      await user.type(screen.getByLabelText('Technology'), 'PostgreSQL');
      await user.type(screen.getByLabelText('Notes'), 'Primary storage');

      const submitButton = screen.getByRole('button', { name: 'Add Node' });
      await user.click(submitButton);

      const calledNode = onAdd.mock.calls[0][0];
      expect(calledNode.type).toBe('database');
      expect(calledNode.label).toBe('PostgreSQL DB');
      expect(calledNode.description).toBe('Main database');
      expect(calledNode.metadata.technology).toBe('PostgreSQL');
      expect(calledNode.metadata.notes).toBe('Primary storage');
    });

    it('generates random position', async () => {
      const user = userEvent.setup();
      const onAdd = vi.fn();
      render(<AddNodeModal {...defaultProps} onAdd={onAdd} />);

      await user.type(screen.getByLabelText('Label *'), 'Test');
      await user.click(screen.getByRole('button', { name: 'Add Node' }));

      const calledNode = onAdd.mock.calls[0][0];
      expect(calledNode.position).toBeDefined();
      expect(calledNode.position.x).toBeGreaterThanOrEqual(100);
      expect(calledNode.position.x).toBeLessThanOrEqual(600);
      expect(calledNode.position.y).toBeGreaterThanOrEqual(100);
      expect(calledNode.position.y).toBeLessThanOrEqual(400);
    });

    it('includes empty arrays for inputs and outputs', async () => {
      const user = userEvent.setup();
      const onAdd = vi.fn();
      render(<AddNodeModal {...defaultProps} onAdd={onAdd} />);

      await user.type(screen.getByLabelText('Label *'), 'Test');
      await user.click(screen.getByRole('button', { name: 'Add Node' }));

      const calledNode = onAdd.mock.calls[0][0];
      expect(calledNode.inputs).toEqual([]);
      expect(calledNode.outputs).toEqual([]);
    });

    it('handles empty optional fields gracefully', async () => {
      const user = userEvent.setup();
      const onAdd = vi.fn();
      render(<AddNodeModal {...defaultProps} onAdd={onAdd} />);

      // Only fill required field
      await user.type(screen.getByLabelText('Label *'), 'Minimal Node');
      await user.click(screen.getByRole('button', { name: 'Add Node' }));

      const calledNode = onAdd.mock.calls[0][0];
      expect(calledNode.description).toBe('');
      expect(calledNode.metadata.technology).toBeNull();
      expect(calledNode.metadata.notes).toBeNull();
    });
  });

  describe('Cancel/Close', () => {
    it('calls onClose when Cancel clicked', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      render(<AddNodeModal {...defaultProps} onClose={onClose} />);

      const cancelButton = screen.getByRole('button', { name: 'Cancel' });
      await user.click(cancelButton);

      expect(onClose).toHaveBeenCalled();
    });

    it('resets form fields on close', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      const { rerender } = render(<AddNodeModal {...defaultProps} onClose={onClose} />);

      // Fill in some fields
      await user.type(screen.getByLabelText('Label *'), 'Test Label');
      await user.selectOptions(screen.getByLabelText('Type *'), 'database');

      // Close and reopen
      const cancelButton = screen.getByRole('button', { name: 'Cancel' });
      await user.click(cancelButton);

      // Modal closed, reopen it
      rerender(<AddNodeModal {...defaultProps} onClose={onClose} isOpen={true} />);

      // Fields should be reset
      expect(screen.getByLabelText('Label *')).toHaveValue('');
      expect(screen.getByLabelText('Type *')).toHaveValue('api');
    });

    it('closes modal after successful submission', async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      const onAdd = vi.fn();
      render(<AddNodeModal {...defaultProps} onClose={onClose} onAdd={onAdd} />);

      await user.type(screen.getByLabelText('Label *'), 'Test');
      await user.click(screen.getByRole('button', { name: 'Add Node' }));

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Button Styling', () => {
    it('renders Cancel as secondary button', () => {
      render(<AddNodeModal {...defaultProps} />);

      const cancelButton = screen.getByRole('button', { name: 'Cancel' });
      expect(cancelButton).toHaveClass('button-secondary');
    });

    it('renders Add Node as primary button', () => {
      render(<AddNodeModal {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: 'Add Node' });
      expect(addButton).toHaveClass('button-primary');
    });
  });

  describe('Form Placeholders', () => {
    it('shows placeholder text in label input', () => {
      render(<AddNodeModal {...defaultProps} />);

      expect(screen.getByPlaceholderText('e.g., User Service')).toBeInTheDocument();
    });

    it('shows placeholder text in description textarea', () => {
      render(<AddNodeModal {...defaultProps} />);

      expect(
        screen.getByPlaceholderText('What does this component do?')
      ).toBeInTheDocument();
    });

    it('shows placeholder text in technology input', () => {
      render(<AddNodeModal {...defaultProps} />);

      expect(
        screen.getByPlaceholderText('e.g., Node.js, PostgreSQL')
      ).toBeInTheDocument();
    });

    it('shows placeholder text in notes textarea', () => {
      render(<AddNodeModal {...defaultProps} />);

      expect(screen.getByPlaceholderText('Additional notes...')).toBeInTheDocument();
    });
  });
});

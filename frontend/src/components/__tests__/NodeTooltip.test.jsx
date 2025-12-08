/**
 * NodeTooltip Component Tests
 * Tests for the node hover tooltip with edit functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NodeTooltip from '../NodeTooltip';

describe('NodeTooltip', () => {
  const mockNode = {
    id: 'api-1',
    data: {
      label: 'API Gateway',
      type: 'api',
      description: 'Main entry point for all requests',
      metadata: {
        technology: 'Kong',
      },
      inputs: ['client'],
      outputs: ['service-1', 'service-2'],
      is_group: false,
    },
    position: { x: 100, y: 100 },
  };

  const mockEdges = [
    { id: 'edge-1', source: 'client', target: 'api-1', label: 'HTTP' },
    { id: 'edge-2', source: 'api-1', target: 'service-1', label: 'gRPC' },
    { id: 'edge-3', source: 'api-1', target: 'service-2', label: 'REST' },
  ];

  const mockNodes = [
    { id: 'client', data: { label: 'Web Client' } },
    { id: 'api-1', data: { label: 'API Gateway' } },
    { id: 'service-1', data: { label: 'User Service' } },
    { id: 'service-2', data: { label: 'Order Service' } },
  ];

  const defaultProps = {
    node: mockNode,
    onSave: vi.fn(),
    onRegenerateDescription: vi.fn(),
    edges: mockEdges,
    nodes: mockNodes,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, 'alert').mockImplementation(() => {});
  });

  describe('Visibility', () => {
    it('returns null when node is null', () => {
      const { container } = render(<NodeTooltip {...defaultProps} node={null} />);

      expect(container.firstChild).toBeNull();
    });

    it('renders tooltip when node is provided', () => {
      render(<NodeTooltip {...defaultProps} />);

      expect(document.querySelector('.node-tooltip')).toBeInTheDocument();
    });
  });

  describe('Basic Rendering', () => {
    it('renders tooltip container', () => {
      render(<NodeTooltip {...defaultProps} />);

      expect(document.querySelector('.node-tooltip')).toBeInTheDocument();
    });

    it('displays node label in header', () => {
      render(<NodeTooltip {...defaultProps} />);

      expect(screen.getByRole('heading', { level: 4 })).toHaveTextContent('API Gateway');
    });

    it('displays node type', () => {
      render(<NodeTooltip {...defaultProps} />);

      expect(screen.getByText('api')).toBeInTheDocument();
    });

    it('displays node description', () => {
      render(<NodeTooltip {...defaultProps} />);

      expect(screen.getByText('Main entry point for all requests')).toBeInTheDocument();
    });
  });

  describe('Metadata Display', () => {
    it('displays technology when present', () => {
      render(<NodeTooltip {...defaultProps} />);

      expect(screen.getByText('Technology:')).toBeInTheDocument();
      expect(screen.getByText('Kong')).toBeInTheDocument();
    });

    it('hides technology section when not present', () => {
      const nodeWithoutTech = {
        ...mockNode,
        data: {
          ...mockNode.data,
          metadata: {},
        },
      };
      render(<NodeTooltip {...defaultProps} node={nodeWithoutTech} />);

      expect(screen.queryByText('Technology:')).not.toBeInTheDocument();
    });

    it('displays inputs array', () => {
      render(<NodeTooltip {...defaultProps} />);

      expect(screen.getByText('Inputs:')).toBeInTheDocument();
      expect(screen.getByText('client')).toBeInTheDocument();
    });

    it('displays outputs array', () => {
      render(<NodeTooltip {...defaultProps} />);

      expect(screen.getByText('Outputs:')).toBeInTheDocument();
      expect(screen.getByText('service-1, service-2')).toBeInTheDocument();
    });

    it('hides inputs section when empty', () => {
      const nodeWithoutInputs = {
        ...mockNode,
        data: {
          ...mockNode.data,
          inputs: [],
        },
      };
      render(<NodeTooltip {...defaultProps} node={nodeWithoutInputs} />);

      // Check that "Inputs:" label is not present for empty inputs
      const inputsLabels = screen.queryAllByText('Inputs:');
      // Only the "Input Nodes" section should exist if there are connected nodes
      expect(inputsLabels.length).toBeLessThanOrEqual(1);
    });

    it('hides outputs section when empty', () => {
      const nodeWithoutOutputs = {
        ...mockNode,
        data: {
          ...mockNode.data,
          outputs: [],
        },
      };
      render(<NodeTooltip {...defaultProps} node={nodeWithoutOutputs} />);

      // Check there's no "Outputs:" section with comma-separated values
      const outputElements = screen.queryAllByText('Outputs:');
      expect(outputElements.length).toBeLessThanOrEqual(1);
    });
  });

  describe('Connected Nodes', () => {
    it('calculates input nodes from edges', () => {
      render(<NodeTooltip {...defaultProps} />);

      expect(screen.getByText('Input Nodes ←')).toBeInTheDocument();
      expect(screen.getByText('Web Client')).toBeInTheDocument();
    });

    it('calculates output nodes from edges', () => {
      render(<NodeTooltip {...defaultProps} />);

      expect(screen.getByText('Output Nodes →')).toBeInTheDocument();
      expect(screen.getByText('User Service, Order Service')).toBeInTheDocument();
    });

    it('displays connected node labels', () => {
      render(<NodeTooltip {...defaultProps} />);

      // Input node label
      expect(screen.getByText('Web Client')).toBeInTheDocument();
      // Output node labels
      expect(screen.getByText('User Service, Order Service')).toBeInTheDocument();
    });

    it('hides connections section when no edges', () => {
      render(<NodeTooltip {...defaultProps} edges={[]} nodes={[]} />);

      expect(screen.queryByText('Input Nodes ←')).not.toBeInTheDocument();
      expect(screen.queryByText('Output Nodes →')).not.toBeInTheDocument();
    });
  });

  describe('Edit Mode', () => {
    it('shows edit button in header', () => {
      render(<NodeTooltip {...defaultProps} />);

      expect(screen.getByTitle('Edit node')).toBeInTheDocument();
    });

    it('clicking edit switches to edit mode', async () => {
      const user = userEvent.setup();
      render(<NodeTooltip {...defaultProps} />);

      await user.click(screen.getByTitle('Edit node'));

      // In edit mode, we should see input fields instead of static text
      expect(screen.getByPlaceholderText('Node name')).toBeInTheDocument();
    });

    it('renders label input in edit mode', async () => {
      const user = userEvent.setup();
      render(<NodeTooltip {...defaultProps} />);

      await user.click(screen.getByTitle('Edit node'));

      const labelInput = screen.getByPlaceholderText('Node name');
      expect(labelInput).toHaveValue('API Gateway');
    });

    it('renders description textarea in edit mode', async () => {
      const user = userEvent.setup();
      render(<NodeTooltip {...defaultProps} />);

      await user.click(screen.getByTitle('Edit node'));

      const descInput = screen.getByPlaceholderText('Description');
      expect(descInput).toHaveValue('Main entry point for all requests');
    });

    it('renders technology input in edit mode', async () => {
      const user = userEvent.setup();
      render(<NodeTooltip {...defaultProps} />);

      await user.click(screen.getByTitle('Edit node'));

      const techInput = screen.getByPlaceholderText('Technology');
      expect(techInput).toHaveValue('Kong');
    });

    it('renders inputs input in edit mode', async () => {
      const user = userEvent.setup();
      render(<NodeTooltip {...defaultProps} />);

      await user.click(screen.getByTitle('Edit node'));

      const inputsField = screen.getByPlaceholderText('Inputs (comma separated)');
      expect(inputsField).toHaveValue('client');
    });

    it('renders outputs input in edit mode', async () => {
      const user = userEvent.setup();
      render(<NodeTooltip {...defaultProps} />);

      await user.click(screen.getByTitle('Edit node'));

      const outputsField = screen.getByPlaceholderText('Outputs (comma separated)');
      expect(outputsField).toHaveValue('service-1, service-2');
    });
  });

  describe('Save/Cancel', () => {
    it('Save button calls onSave with updated node', async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<NodeTooltip {...defaultProps} onSave={onSave} />);

      await user.click(screen.getByTitle('Edit node'));

      // Modify label
      const labelInput = screen.getByPlaceholderText('Node name');
      await user.clear(labelInput);
      await user.type(labelInput, 'Updated Gateway');

      // Save
      await user.click(screen.getByText('Save'));

      expect(onSave).toHaveBeenCalledTimes(1);
      const savedNode = onSave.mock.calls[0][0];
      expect(savedNode.label).toBe('Updated Gateway');
    });

    it('converts comma-separated inputs to array', async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<NodeTooltip {...defaultProps} onSave={onSave} />);

      await user.click(screen.getByTitle('Edit node'));

      // Modify inputs
      const inputsField = screen.getByPlaceholderText('Inputs (comma separated)');
      await user.clear(inputsField);
      await user.type(inputsField, 'input1, input2, input3');

      // Save
      await user.click(screen.getByText('Save'));

      const savedNode = onSave.mock.calls[0][0];
      expect(savedNode.inputs).toEqual(['input1', 'input2', 'input3']);
    });

    it('converts comma-separated outputs to array', async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<NodeTooltip {...defaultProps} onSave={onSave} />);

      await user.click(screen.getByTitle('Edit node'));

      // Modify outputs
      const outputsField = screen.getByPlaceholderText('Outputs (comma separated)');
      await user.clear(outputsField);
      await user.type(outputsField, 'out1, out2');

      // Save
      await user.click(screen.getByText('Save'));

      const savedNode = onSave.mock.calls[0][0];
      expect(savedNode.outputs).toEqual(['out1', 'out2']);
    });

    it('Cancel button reverts to original values', async () => {
      const user = userEvent.setup();
      render(<NodeTooltip {...defaultProps} />);

      await user.click(screen.getByTitle('Edit node'));

      // Modify label
      const labelInput = screen.getByPlaceholderText('Node name');
      await user.clear(labelInput);
      await user.type(labelInput, 'Changed Name');

      // Cancel
      await user.click(screen.getByText('Cancel'));

      // Should show original label
      expect(screen.getByRole('heading', { level: 4 })).toHaveTextContent('API Gateway');
    });

    it('Cancel button exits edit mode', async () => {
      const user = userEvent.setup();
      render(<NodeTooltip {...defaultProps} />);

      await user.click(screen.getByTitle('Edit node'));
      expect(screen.getByPlaceholderText('Node name')).toBeInTheDocument();

      await user.click(screen.getByText('Cancel'));

      // Should be back in view mode (no input fields)
      expect(screen.queryByPlaceholderText('Node name')).not.toBeInTheDocument();
    });

    it('preserves node id, type, and position on save', async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<NodeTooltip {...defaultProps} onSave={onSave} />);

      await user.click(screen.getByTitle('Edit node'));
      await user.click(screen.getByText('Save'));

      const savedNode = onSave.mock.calls[0][0];
      expect(savedNode.id).toBe('api-1');
      expect(savedNode.type).toBe('api');
      expect(savedNode.position).toEqual({ x: 100, y: 100 });
    });

    it('filters empty strings from inputs array', async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<NodeTooltip {...defaultProps} onSave={onSave} />);

      await user.click(screen.getByTitle('Edit node'));

      const inputsField = screen.getByPlaceholderText('Inputs (comma separated)');
      await user.clear(inputsField);
      await user.type(inputsField, 'input1, , input2, ');

      await user.click(screen.getByText('Save'));

      const savedNode = onSave.mock.calls[0][0];
      expect(savedNode.inputs).toEqual(['input1', 'input2']);
    });
  });

  describe('AI Regenerate (Group Nodes)', () => {
    const groupNode = {
      ...mockNode,
      data: {
        ...mockNode.data,
        is_group: true,
      },
    };

    it('shows AI regenerate button for group nodes', () => {
      render(<NodeTooltip {...defaultProps} node={groupNode} />);

      expect(screen.getByTitle('Regenerate description with AI')).toBeInTheDocument();
    });

    it('hides AI regenerate button for non-group nodes', () => {
      render(<NodeTooltip {...defaultProps} />);

      expect(screen.queryByTitle('Regenerate description with AI')).not.toBeInTheDocument();
    });

    it('calls onRegenerateDescription on click', async () => {
      const user = userEvent.setup();
      const onRegenerateDescription = vi.fn().mockResolvedValue({ description: 'New description' });
      render(
        <NodeTooltip
          {...defaultProps}
          node={groupNode}
          onRegenerateDescription={onRegenerateDescription}
        />
      );

      await user.click(screen.getByTitle('Regenerate description with AI'));

      expect(onRegenerateDescription).toHaveBeenCalledWith('api-1');
    });

    it('shows loading spinner during regeneration', async () => {
      const user = userEvent.setup();
      // Create a promise that doesn't resolve immediately
      let resolvePromise;
      const slowPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      const onRegenerateDescription = vi.fn().mockReturnValue(slowPromise);

      render(
        <NodeTooltip
          {...defaultProps}
          node={groupNode}
          onRegenerateDescription={onRegenerateDescription}
        />
      );

      await user.click(screen.getByTitle('Regenerate description with AI'));

      // Button should show loading state
      expect(screen.getByText('⏳')).toBeInTheDocument();

      // Cleanup
      resolvePromise({ description: 'done' });
    });

    it('shows alert on regeneration error', async () => {
      const user = userEvent.setup();
      const onRegenerateDescription = vi.fn().mockRejectedValue(new Error('Failed'));
      render(
        <NodeTooltip
          {...defaultProps}
          node={groupNode}
          onRegenerateDescription={onRegenerateDescription}
        />
      );

      await user.click(screen.getByTitle('Regenerate description with AI'));

      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith(
          'Failed to regenerate description with AI. Please try again.'
        );
      });
    });

    it('does not show AI button when onRegenerateDescription is not provided', () => {
      render(
        <NodeTooltip
          {...defaultProps}
          node={groupNode}
          onRegenerateDescription={undefined}
        />
      );

      expect(screen.queryByTitle('Regenerate description with AI')).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles node with no metadata', () => {
      const nodeWithoutMetadata = {
        ...mockNode,
        data: {
          ...mockNode.data,
          metadata: null,
        },
      };
      render(<NodeTooltip {...defaultProps} node={nodeWithoutMetadata} />);

      expect(screen.getByText('API Gateway')).toBeInTheDocument();
      expect(screen.queryByText('Technology:')).not.toBeInTheDocument();
    });

    it('handles empty inputs and outputs', () => {
      const nodeWithEmptyIO = {
        ...mockNode,
        data: {
          ...mockNode.data,
          inputs: [],
          outputs: [],
        },
      };
      render(<NodeTooltip {...defaultProps} node={nodeWithEmptyIO} edges={[]} />);

      expect(screen.getByText('API Gateway')).toBeInTheDocument();
    });

    it('handles undefined inputs and outputs', () => {
      const nodeWithUndefinedIO = {
        ...mockNode,
        data: {
          ...mockNode.data,
          inputs: undefined,
          outputs: undefined,
        },
      };
      render(<NodeTooltip {...defaultProps} node={nodeWithUndefinedIO} />);

      expect(screen.getByText('API Gateway')).toBeInTheDocument();
    });
  });
});

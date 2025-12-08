/**
 * Tests for CustomNode component
 *
 * CustomNode is the React Flow node component that renders different types
 * of architecture components (api, database, cache, etc.)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CustomNode from '../CustomNode'

// Mock React Flow's Handle component
vi.mock('reactflow', () => ({
  Handle: ({ type, position }) => (
    <div data-testid={`handle-${type}`} data-position={position} />
  ),
  Position: {
    Top: 'top',
    Bottom: 'bottom',
    Left: 'left',
    Right: 'right',
  },
}))

describe('CustomNode', () => {
  const defaultProps = {
    id: 'test-node-1',
    data: {
      label: 'API Gateway',
      type: 'gateway',
      onDelete: vi.fn(),
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic rendering', () => {
    it('renders node label correctly', () => {
      render(<CustomNode {...defaultProps} />)
      expect(screen.getByText('API Gateway')).toBeInTheDocument()
    })

    it('renders node type badge', () => {
      render(<CustomNode {...defaultProps} />)
      expect(screen.getByText('gateway')).toBeInTheDocument()
    })

    it('applies correct CSS class for node type', () => {
      const { container } = render(<CustomNode {...defaultProps} />)
      expect(container.firstChild).toHaveClass('node-type-gateway')
    })

    it('renders handles for connections', () => {
      render(<CustomNode {...defaultProps} />)
      expect(screen.getByTestId('handle-target')).toBeInTheDocument()
      expect(screen.getByTestId('handle-source')).toBeInTheDocument()
    })
  })

  describe('Different node types', () => {
    const nodeTypes = ['database', 'cache', 'api', 'server', 'loadbalancer', 'queue', 'cdn', 'gateway', 'storage', 'service']

    nodeTypes.forEach(type => {
      it(`renders ${type} node with correct class`, () => {
        const props = {
          ...defaultProps,
          data: { ...defaultProps.data, type },
        }
        const { container } = render(<CustomNode {...props} />)
        expect(container.firstChild).toHaveClass(`node-type-${type}`)
      })
    })
  })

  describe('Hover interactions', () => {
    it('shows delete button on hover', () => {
      const { container } = render(<CustomNode {...defaultProps} />)
      const node = container.firstChild

      // Initially no delete button visible
      expect(screen.queryByTitle('Delete node')).not.toBeInTheDocument()

      // Hover over node
      fireEvent.mouseEnter(node)

      // Delete button should be visible
      expect(screen.getByTitle('Delete node')).toBeInTheDocument()

      // Mouse leave
      fireEvent.mouseLeave(node)

      // Delete button should be hidden again
      expect(screen.queryByTitle('Delete node')).not.toBeInTheDocument()
    })

    it('calls onDelete when delete button is clicked', () => {
      const onDelete = vi.fn()
      const props = {
        ...defaultProps,
        data: { ...defaultProps.data, onDelete },
      }
      const { container } = render(<CustomNode {...props} />)

      // Hover to show delete button
      fireEvent.mouseEnter(container.firstChild)

      // Click delete
      fireEvent.click(screen.getByTitle('Delete node'))

      expect(onDelete).toHaveBeenCalledWith('test-node-1')
    })
  })

  describe('Group nodes', () => {
    const groupProps = {
      id: 'group-1',
      data: {
        label: 'Backend Services',
        type: 'group',
        is_group: true,
        is_collapsed: false,
        child_ids: ['child-1', 'child-2', 'child-3'],
        onToggleCollapse: vi.fn(),
      },
    }

    it('renders group with correct class', () => {
      const { container } = render(<CustomNode {...groupProps} />)
      expect(container.firstChild).toHaveClass('node-group')
    })

    it('displays child count', () => {
      render(<CustomNode {...groupProps} />)
      expect(screen.getByText('3 nodes')).toBeInTheDocument()
    })

    it('displays singular "node" for single child', () => {
      const props = {
        ...groupProps,
        data: { ...groupProps.data, child_ids: ['child-1'] },
      }
      render(<CustomNode {...props} />)
      expect(screen.getByText('1 node')).toBeInTheDocument()
    })

    it('shows collapse button when expanded', () => {
      render(<CustomNode {...groupProps} />)
      expect(screen.getByTitle('Collapse group')).toBeInTheDocument()
      expect(screen.getByText('▼')).toBeInTheDocument()
    })

    it('shows expand button when collapsed', () => {
      const props = {
        ...groupProps,
        data: { ...groupProps.data, is_collapsed: true },
      }
      render(<CustomNode {...props} />)
      expect(screen.getByTitle('Expand group')).toBeInTheDocument()
      expect(screen.getByText('▶')).toBeInTheDocument()
    })

    it('calls onToggleCollapse when collapse button is clicked', () => {
      const onToggleCollapse = vi.fn()
      const props = {
        ...groupProps,
        data: { ...groupProps.data, onToggleCollapse },
      }
      render(<CustomNode {...props} />)

      fireEvent.click(screen.getByTitle('Collapse group'))

      expect(onToggleCollapse).toHaveBeenCalledWith('group-1')
    })
  })

  describe('Child nodes (with parent)', () => {
    const childProps = {
      id: 'child-node-1',
      data: {
        label: 'Child Service',
        type: 'service',
        parent_id: 'parent-group-1',
        onToggleCollapse: vi.fn(),
      },
    }

    it('shows regroup button on hover for child nodes', () => {
      const { container } = render(<CustomNode {...childProps} />)

      // Initially no regroup button
      expect(screen.queryByTitle('Collapse group')).not.toBeInTheDocument()

      // Hover over node
      fireEvent.mouseEnter(container.firstChild)

      // Regroup button should be visible (titled "Collapse group")
      const regroupButton = screen.getByTitle('Collapse group')
      expect(regroupButton).toBeInTheDocument()
    })

    it('calls onToggleCollapse with parent ID when regroup button clicked', () => {
      const onToggleCollapse = vi.fn()
      const props = {
        ...childProps,
        data: { ...childProps.data, onToggleCollapse },
      }
      const { container } = render(<CustomNode {...props} />)

      // Hover to show button
      fireEvent.mouseEnter(container.firstChild)

      // Click regroup
      fireEvent.click(screen.getByTitle('Collapse group'))

      expect(onToggleCollapse).toHaveBeenCalledWith('parent-group-1')
    })
  })

  describe('Drop target state', () => {
    it('shows drop hint when node is a drop target', () => {
      const props = {
        ...defaultProps,
        data: { ...defaultProps.data, isDropTarget: true },
      }
      render(<CustomNode {...props} />)

      expect(screen.getByText('Drop to merge')).toBeInTheDocument()
    })

    it('applies drop-target class when is drop target', () => {
      const props = {
        ...defaultProps,
        data: { ...defaultProps.data, isDropTarget: true },
      }
      const { container } = render(<CustomNode {...props} />)

      expect(container.firstChild).toHaveClass('drop-target')
    })

    it('does not show drop hint when not a drop target', () => {
      render(<CustomNode {...defaultProps} />)
      expect(screen.queryByText('Drop to merge')).not.toBeInTheDocument()
    })
  })

  describe('Blended color for mixed groups', () => {
    it('applies blended color style', () => {
      const props = {
        ...defaultProps,
        data: {
          ...defaultProps.data,
          blendedColor: '#ff5733',
        },
      }
      const { container } = render(<CustomNode {...props} />)

      expect(container.firstChild).toHaveStyle({
        backgroundColor: '#ff5733',
      })
    })
  })

  describe('Event propagation', () => {
    it('stops propagation on delete click', () => {
      const parentClickHandler = vi.fn()
      const props = {
        ...defaultProps,
        data: { ...defaultProps.data, onDelete: vi.fn() },
      }

      const { container } = render(
        <div onClick={parentClickHandler}>
          <CustomNode {...props} />
        </div>
      )

      // Hover to show delete button
      fireEvent.mouseEnter(container.querySelector('.custom-node'))
      fireEvent.click(screen.getByTitle('Delete node'))

      // Parent click handler should NOT be called
      expect(parentClickHandler).not.toHaveBeenCalled()
    })
  })
})

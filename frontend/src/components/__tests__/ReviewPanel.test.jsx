import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ReviewPanel from '../ReviewPanel';

const review = {
  score: 63,
  summary: 'A single-region API with one database.',
  counts: { critical: 1, high: 1, medium: 0, low: 0 },
  findings: [
    {
      id: 'finding-1',
      severity: 'critical',
      category: 'reliability',
      title: 'Database is a single point of failure',
      detail: 'All writes go to one Postgres instance with no replica.',
      node_ids: ['db_1'],
      recommendation: 'Add a read replica and enable automated failover.',
    },
    {
      id: 'finding-2',
      severity: 'high',
      category: 'security',
      title: 'Database reachable from the edge',
      detail: 'The load balancer routes straight to the database.',
      node_ids: ['db_1', 'lb_1'],
      recommendation: 'Put the API tier between them.',
    },
  ],
};

describe('ReviewPanel', () => {
  const defaultProps = {
    review,
    isGenerating: false,
    isStale: false,
    error: null,
    onClose: vi.fn(),
    onRerun: vi.fn(),
    onHighlightNodes: vi.fn(),
    onFixFinding: vi.fn(),
    onWidthChange: vi.fn(),
  };

  beforeEach(() => vi.clearAllMocks());

  it('renders the score and severity breakdown', () => {
    render(<ReviewPanel {...defaultProps} />);
    expect(screen.getByText('63')).toBeInTheDocument();
    expect(screen.getByText('1 critical')).toBeInTheDocument();
    expect(screen.getByText('1 high')).toBeInTheDocument();
  });

  it('lists findings most severe first', () => {
    const { container } = render(<ReviewPanel {...defaultProps} />);
    const titles = [...container.querySelectorAll('.review-finding-title')].map((n) => n.textContent);
    expect(titles[0]).toBe('Database is a single point of failure');
  });

  describe('fix workflow', () => {
    it('hands the finding to the parent when Ask Sketch to fix this is clicked', () => {
      const onFixFinding = vi.fn();
      render(<ReviewPanel {...defaultProps} onFixFinding={onFixFinding} />);

      // The action lives inside the expanded body, so open the finding first.
      fireEvent.click(screen.getByText('Database is a single point of failure'));
      fireEvent.click(screen.getByText('Ask Sketch to fix this'));

      expect(onFixFinding).toHaveBeenCalledTimes(1);
      const passed = onFixFinding.mock.calls[0][0];
      expect(passed.id).toBe('finding-1');
      expect(passed.recommendation).toContain('read replica');
      expect(passed.node_ids).toEqual(['db_1']);
    });

    it('does not throw when a finding has no node_ids', () => {
      const bare = {
        ...review,
        findings: [{ ...review.findings[0], node_ids: [] }],
      };
      render(<ReviewPanel {...defaultProps} review={bare} />);

      fireEvent.click(screen.getByText('Database is a single point of failure'));
      expect(() => fireEvent.click(screen.getByText('Ask Sketch to fix this'))).not.toThrow();
    });
  });

  describe('node highlighting', () => {
    it('highlights a finding\'s nodes when expanded and clears them when collapsed', () => {
      const onHighlightNodes = vi.fn();
      render(<ReviewPanel {...defaultProps} onHighlightNodes={onHighlightNodes} />);

      fireEvent.click(screen.getByText('Database reachable from the edge'));
      expect(onHighlightNodes).toHaveBeenLastCalledWith(['db_1', 'lb_1']);

      fireEvent.click(screen.getByText('Database reachable from the edge'));
      expect(onHighlightNodes).toHaveBeenLastCalledWith([]);
    });

    it('clears the highlight when the panel unmounts', () => {
      const onHighlightNodes = vi.fn();
      const { unmount } = render(
        <ReviewPanel {...defaultProps} onHighlightNodes={onHighlightNodes} />
      );

      unmount();
      expect(onHighlightNodes).toHaveBeenLastCalledWith([]);
    });
  });

  describe('stale state', () => {
    it('warns and offers a re-run once the diagram has moved on', () => {
      const onRerun = vi.fn();
      render(<ReviewPanel {...defaultProps} isStale onRerun={onRerun} />);

      expect(screen.getByText(/no longer match what is on the canvas/)).toBeInTheDocument();
      fireEvent.click(screen.getByText(/Re-run \(5 credits\)/));
      expect(onRerun).toHaveBeenCalledTimes(1);
    });

    it('shows no stale banner on a fresh review', () => {
      render(<ReviewPanel {...defaultProps} />);
      expect(screen.queryByText(/no longer match what is on the canvas/)).not.toBeInTheDocument();
    });
  });

  describe('credit disclosure', () => {
    it('states the cost on every button that spends credits', () => {
      const { rerender, container } = render(<ReviewPanel {...defaultProps} />);
      expect(container.textContent).toMatch(/Re-run review \(5 credits\)/);

      rerender(<ReviewPanel {...defaultProps} review={null} />);
      expect(container.textContent).toMatch(/Run review \(5 credits\)/);

      rerender(<ReviewPanel {...defaultProps} review={null} error="boom" />);
      expect(container.textContent).toMatch(/Try again \(5 credits\)/);
    });
  });

  describe('empty and loading states', () => {
    it('reports a clean design without inventing findings', () => {
      const clean = { score: 100, summary: 'Solid.', counts: {}, findings: [] };
      render(<ReviewPanel {...defaultProps} review={clean} />);

      expect(screen.getByText('100')).toBeInTheDocument();
      expect(screen.getByText('No issues found')).toBeInTheDocument();
    });

    it('shows progress while generating', () => {
      render(<ReviewPanel {...defaultProps} review={null} isGenerating />);
      expect(screen.getByText(/Reviewing your architecture/)).toBeInTheDocument();
    });
  });

  // Regression: this panel and the design-doc panel are both position:fixed and
  // dock to the same edge. They originally shared one offset (the session-history
  // sidebar width), so opening both stacked them and only one was visible.
  describe('docking alongside the design doc panel', () => {
    const panelOf = (container) => container.querySelector('.review-panel');

    it('sits flush left when nothing else is docked', () => {
      const { container } = render(<ReviewPanel {...defaultProps} leftOffset={0} />);
      expect(panelOf(container).style.left).toBe('0px');
    });

    it('clears the session-history sidebar', () => {
      const { container } = render(<ReviewPanel {...defaultProps} leftOffset={300} />);
      expect(panelOf(container).style.left).toBe('300px');
    });

    it('clears the sidebar and the design doc panel together', () => {
      // 300 sidebar + 400 design doc: without this the two panels overlapped.
      const { container } = render(<ReviewPanel {...defaultProps} leftOffset={700} />);
      expect(panelOf(container).style.left).toBe('700px');
    });

    it('has a width of its own so it never covers the panel to its left', () => {
      const { container } = render(<ReviewPanel {...defaultProps} leftOffset={400} />);
      const panel = panelOf(container);
      expect(panel.style.left).toBe('400px');
      expect(parseInt(panel.style.width, 10)).toBeGreaterThan(0);
    });
  });
});

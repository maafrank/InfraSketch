/**
 * Layout Utility Tests
 * Tests for dagre-based auto-layout functionality
 */

import { describe, it, expect } from 'vitest';
import { getLayoutedElements } from '../layout';

describe('getLayoutedElements', () => {
  describe('Basic functionality', () => {
    it('returns empty array for empty nodes', () => {
      const result = getLayoutedElements([], []);

      expect(result).toEqual([]);
    });

    it('positions a single node', () => {
      const nodes = [{ id: 'node-1', data: { label: 'Test' } }];
      const edges = [];

      const result = getLayoutedElements(nodes, edges);

      expect(result).toHaveLength(1);
      expect(result[0].id).toBe('node-1');
      expect(result[0].position).toBeDefined();
      expect(typeof result[0].position.x).toBe('number');
      expect(typeof result[0].position.y).toBe('number');
    });

    it('preserves original node properties', () => {
      const nodes = [
        {
          id: 'node-1',
          type: 'database',
          data: { label: 'PostgreSQL', description: 'Main DB' },
          someCustomProp: 'custom value',
        },
      ];

      const result = getLayoutedElements(nodes, []);

      expect(result[0].type).toBe('database');
      expect(result[0].data).toEqual({ label: 'PostgreSQL', description: 'Main DB' });
      expect(result[0].someCustomProp).toBe('custom value');
    });
  });

  describe('Multi-node layouts', () => {
    it('positions multiple nodes with edges', () => {
      const nodes = [
        { id: 'api', data: { label: 'API' } },
        { id: 'service', data: { label: 'Service' } },
        { id: 'db', data: { label: 'Database' } },
      ];
      const edges = [
        { id: 'e1', source: 'api', target: 'service' },
        { id: 'e2', source: 'service', target: 'db' },
      ];

      const result = getLayoutedElements(nodes, edges);

      expect(result).toHaveLength(3);

      // All nodes should have positions
      result.forEach((node) => {
        expect(node.position).toBeDefined();
        expect(node.position.x).toBeDefined();
        expect(node.position.y).toBeDefined();
      });

      // With TB direction, downstream nodes should have higher y values
      const apiNode = result.find((n) => n.id === 'api');
      const serviceNode = result.find((n) => n.id === 'service');
      const dbNode = result.find((n) => n.id === 'db');

      // In top-bottom layout, source should be above target
      expect(apiNode.position.y).toBeLessThan(serviceNode.position.y);
      expect(serviceNode.position.y).toBeLessThan(dbNode.position.y);
    });

    it('positions disconnected nodes', () => {
      const nodes = [
        { id: 'node-1', data: { label: 'Node 1' } },
        { id: 'node-2', data: { label: 'Node 2' } },
        { id: 'node-3', data: { label: 'Node 3' } },
      ];
      const edges = []; // No connections

      const result = getLayoutedElements(nodes, edges);

      expect(result).toHaveLength(3);

      // Each node should have valid positions
      result.forEach((node) => {
        expect(Number.isFinite(node.position.x)).toBe(true);
        expect(Number.isFinite(node.position.y)).toBe(true);
      });
    });

    it('handles complex graph with multiple branches', () => {
      const nodes = [
        { id: 'gateway', data: { label: 'Gateway' } },
        { id: 'auth-service', data: { label: 'Auth' } },
        { id: 'user-service', data: { label: 'User' } },
        { id: 'auth-db', data: { label: 'Auth DB' } },
        { id: 'user-db', data: { label: 'User DB' } },
      ];
      const edges = [
        { id: 'e1', source: 'gateway', target: 'auth-service' },
        { id: 'e2', source: 'gateway', target: 'user-service' },
        { id: 'e3', source: 'auth-service', target: 'auth-db' },
        { id: 'e4', source: 'user-service', target: 'user-db' },
      ];

      const result = getLayoutedElements(nodes, edges);

      expect(result).toHaveLength(5);

      const gateway = result.find((n) => n.id === 'gateway');
      const authService = result.find((n) => n.id === 'auth-service');
      const userService = result.find((n) => n.id === 'user-service');

      // Gateway should be at the top (smallest y)
      expect(gateway.position.y).toBeLessThan(authService.position.y);
      expect(gateway.position.y).toBeLessThan(userService.position.y);

      // Auth and user services should be at similar y levels (same rank)
      expect(Math.abs(authService.position.y - userService.position.y)).toBeLessThan(10);
    });
  });

  describe('Direction options', () => {
    const nodes = [
      { id: 'source', data: { label: 'Source' } },
      { id: 'target', data: { label: 'Target' } },
    ];
    const edges = [{ id: 'e1', source: 'source', target: 'target' }];

    it('applies top-bottom (TB) direction by default', () => {
      const result = getLayoutedElements(nodes, edges);

      const sourceNode = result.find((n) => n.id === 'source');
      const targetNode = result.find((n) => n.id === 'target');

      // Source should be above target in TB direction
      expect(sourceNode.position.y).toBeLessThan(targetNode.position.y);
    });

    it('applies top-bottom (TB) direction when specified', () => {
      const result = getLayoutedElements(nodes, edges, 'TB');

      const sourceNode = result.find((n) => n.id === 'source');
      const targetNode = result.find((n) => n.id === 'target');

      expect(sourceNode.position.y).toBeLessThan(targetNode.position.y);
    });

    it('applies left-right (LR) direction when specified', () => {
      const result = getLayoutedElements(nodes, edges, 'LR');

      const sourceNode = result.find((n) => n.id === 'source');
      const targetNode = result.find((n) => n.id === 'target');

      // Source should be to the left of target in LR direction
      expect(sourceNode.position.x).toBeLessThan(targetNode.position.x);
    });
  });

  describe('Edge cases', () => {
    it('handles circular dependencies gracefully', () => {
      const nodes = [
        { id: 'a', data: { label: 'A' } },
        { id: 'b', data: { label: 'B' } },
        { id: 'c', data: { label: 'C' } },
      ];
      const edges = [
        { id: 'e1', source: 'a', target: 'b' },
        { id: 'e2', source: 'b', target: 'c' },
        { id: 'e3', source: 'c', target: 'a' }, // Creates cycle
      ];

      // Should not throw
      const result = getLayoutedElements(nodes, edges);

      expect(result).toHaveLength(3);
      result.forEach((node) => {
        expect(Number.isFinite(node.position.x)).toBe(true);
        expect(Number.isFinite(node.position.y)).toBe(true);
      });
    });

    it('handles self-referencing edges', () => {
      const nodes = [{ id: 'node-1', data: { label: 'Self-referencing' } }];
      const edges = [{ id: 'e1', source: 'node-1', target: 'node-1' }];

      const result = getLayoutedElements(nodes, edges);

      expect(result).toHaveLength(1);
      expect(Number.isFinite(result[0].position.x)).toBe(true);
      expect(Number.isFinite(result[0].position.y)).toBe(true);
    });

    it('handles nodes with existing positions', () => {
      const nodes = [
        {
          id: 'node-1',
          data: { label: 'Test' },
          position: { x: 999, y: 999 }, // Existing position should be replaced
        },
      ];

      const result = getLayoutedElements(nodes, []);

      // Position should be recalculated, not preserved
      expect(result[0].position).toBeDefined();
      // The exact values depend on dagre, but it should have calculated new positions
    });

    it('handles nodes with special characters in IDs', () => {
      const nodes = [
        { id: 'node-with-dashes', data: { label: 'Dashes' } },
        { id: 'node_with_underscores', data: { label: 'Underscores' } },
        { id: 'node.with.dots', data: { label: 'Dots' } },
      ];
      const edges = [
        { id: 'e1', source: 'node-with-dashes', target: 'node_with_underscores' },
        { id: 'e2', source: 'node_with_underscores', target: 'node.with.dots' },
      ];

      const result = getLayoutedElements(nodes, edges);

      expect(result).toHaveLength(3);
      result.forEach((node) => {
        expect(node.position).toBeDefined();
      });
    });

    it('handles large number of nodes', () => {
      const nodes = Array.from({ length: 50 }, (_, i) => ({
        id: `node-${i}`,
        data: { label: `Node ${i}` },
      }));

      // Create a chain of edges
      const edges = Array.from({ length: 49 }, (_, i) => ({
        id: `edge-${i}`,
        source: `node-${i}`,
        target: `node-${i + 1}`,
      }));

      const result = getLayoutedElements(nodes, edges);

      expect(result).toHaveLength(50);

      // First node should be above last node in TB layout
      const firstNode = result.find((n) => n.id === 'node-0');
      const lastNode = result.find((n) => n.id === 'node-49');
      expect(firstNode.position.y).toBeLessThan(lastNode.position.y);
    });
  });

  describe('Node spacing', () => {
    it('maintains reasonable spacing between adjacent nodes', () => {
      const nodes = [
        { id: 'node-1', data: { label: 'Node 1' } },
        { id: 'node-2', data: { label: 'Node 2' } },
      ];
      const edges = [{ id: 'e1', source: 'node-1', target: 'node-2' }];

      const result = getLayoutedElements(nodes, edges);

      const node1 = result.find((n) => n.id === 'node-1');
      const node2 = result.find((n) => n.id === 'node-2');

      // Nodes should have some spacing (not overlapping)
      const yDiff = Math.abs(node2.position.y - node1.position.y);
      expect(yDiff).toBeGreaterThan(50); // At least some vertical spacing
    });

    it('spaces sibling nodes horizontally in TB layout', () => {
      const nodes = [
        { id: 'parent', data: { label: 'Parent' } },
        { id: 'child-1', data: { label: 'Child 1' } },
        { id: 'child-2', data: { label: 'Child 2' } },
      ];
      const edges = [
        { id: 'e1', source: 'parent', target: 'child-1' },
        { id: 'e2', source: 'parent', target: 'child-2' },
      ];

      const result = getLayoutedElements(nodes, edges, 'TB');

      const child1 = result.find((n) => n.id === 'child-1');
      const child2 = result.find((n) => n.id === 'child-2');

      // Children should be at same y level but different x positions
      expect(Math.abs(child1.position.y - child2.position.y)).toBeLessThan(10);
      expect(child1.position.x).not.toBe(child2.position.x);
    });
  });
});

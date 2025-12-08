/**
 * API Client Tests
 * Tests for all backend API communication functions
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../../tests/mocks/server';
import { mockDiagram, mockSession, mockUserSessions } from '../../../tests/mocks/handlers';
import {
  generateDiagram,
  getDiagramStatus,
  pollDiagramStatus,
  sendChatMessage,
  getSession,
  createBlankSession,
  addNode,
  deleteNode,
  updateNode,
  addEdge,
  deleteEdge,
  createNodeGroup,
  ungroupNodes,
  toggleGroupCollapse,
  generateDesignDoc,
  getDesignDocStatus,
  pollDesignDocStatus,
  updateDesignDoc,
  exportDesignDoc,
  getUserSessions,
  renameSession,
  deleteSession,
  setClerkTokenGetter,
} from '../client';

const API_URL = 'http://localhost:8000/api';

describe('API Client', () => {
  beforeEach(() => {
    // Reset any request interceptor state
    vi.clearAllMocks();
  });

  describe('generateDiagram', () => {
    it('sends prompt and returns session info', async () => {
      const result = await generateDiagram('Create a user auth system');

      expect(result).toEqual({
        session_id: 'test-session-123',
        status: 'generating',
      });
    });

    it('sends model parameter when provided', async () => {
      let capturedBody;
      server.use(
        http.post(`${API_URL}/generate`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ session_id: 'test-123', status: 'generating' });
        })
      );

      await generateDiagram('Test prompt', 'claude-sonnet-4-5');

      expect(capturedBody).toEqual({
        prompt: 'Test prompt',
        model: 'claude-sonnet-4-5',
      });
    });
  });

  describe('getDiagramStatus', () => {
    it('returns diagram status', async () => {
      const result = await getDiagramStatus('test-session-123');

      expect(result.status).toBe('completed');
      expect(result.diagram).toEqual(mockDiagram);
      expect(result.name).toBe('Test Diagram');
    });
  });

  describe('pollDiagramStatus', () => {
    it('polls until completed', async () => {
      let callCount = 0;
      server.use(
        http.get(`${API_URL}/session/:sessionId/diagram/status`, () => {
          callCount++;
          if (callCount < 3) {
            return HttpResponse.json({ status: 'generating', elapsed_seconds: callCount });
          }
          return HttpResponse.json({
            status: 'completed',
            diagram: mockDiagram,
            messages: [],
            name: 'Test',
            duration_seconds: 5,
          });
        })
      );

      const result = await pollDiagramStatus('test-session-123');

      expect(result.success).toBe(true);
      expect(result.diagram).toEqual(mockDiagram);
      expect(callCount).toBe(3);
    });

    it('calls onProgress callback during polling', async () => {
      let callCount = 0;
      server.use(
        http.get(`${API_URL}/session/:sessionId/diagram/status`, () => {
          callCount++;
          if (callCount < 2) {
            return HttpResponse.json({ status: 'generating', elapsed_seconds: callCount });
          }
          return HttpResponse.json({
            status: 'completed',
            diagram: mockDiagram,
            messages: [],
            name: 'Test',
          });
        })
      );

      const progressUpdates = [];
      await pollDiagramStatus('test-123', (status) => progressUpdates.push(status));

      expect(progressUpdates.length).toBeGreaterThanOrEqual(1);
      expect(progressUpdates[0].status).toBe('generating');
    });

    it('returns failure on failed status', async () => {
      server.use(
        http.get(`${API_URL}/session/:sessionId/diagram/status`, () => {
          return HttpResponse.json({
            status: 'failed',
            error: 'Generation failed due to invalid prompt',
          });
        })
      );

      const result = await pollDiagramStatus('test-123');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Generation failed due to invalid prompt');
    });

    it('times out after maxWaitTime', async () => {
      server.use(
        http.get(`${API_URL}/session/:sessionId/diagram/status`, () => {
          return HttpResponse.json({ status: 'generating' });
        })
      );

      // Use a very short timeout for testing
      const result = await pollDiagramStatus('test-123', null, 100);

      expect(result.success).toBe(false);
      expect(result.error).toContain('timed out');
    });
  });

  describe('sendChatMessage', () => {
    it('sends message and returns response', async () => {
      const result = await sendChatMessage('session-123', 'Add a cache layer');

      expect(result.response).toContain('Add a cache layer');
    });

    it('includes nodeId when provided', async () => {
      let capturedBody;
      server.use(
        http.post(`${API_URL}/chat`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ response: 'OK', diagram: null });
        })
      );

      await sendChatMessage('session-123', 'Update this node', 'node-1', 'claude-haiku-4-5');

      expect(capturedBody).toEqual({
        session_id: 'session-123',
        message: 'Update this node',
        node_id: 'node-1',
        model: 'claude-haiku-4-5',
      });
    });
  });

  describe('getSession', () => {
    it('retrieves session data', async () => {
      const result = await getSession('test-session-123');

      expect(result.session_id).toBe('test-session-123');
      expect(result.diagram).toEqual(mockDiagram);
    });
  });

  describe('createBlankSession', () => {
    it('creates new empty session', async () => {
      const result = await createBlankSession();

      expect(result.session_id).toBe('new-blank-session');
      expect(result.diagram).toEqual({ nodes: [], edges: [] });
    });
  });

  describe('Node CRUD operations', () => {
    const testNode = {
      id: 'new-node-1',
      type: 'cache',
      label: 'Redis Cache',
      description: 'Caching layer',
      position: { x: 300, y: 200 },
    };

    it('addNode adds a node and returns updated diagram', async () => {
      const result = await addNode('session-123', testNode);

      expect(result.nodes).toContainEqual(testNode);
    });

    it('deleteNode removes node and returns updated diagram', async () => {
      const result = await deleteNode('session-123', 'api-1');

      expect(result.nodes.find(n => n.id === 'api-1')).toBeUndefined();
    });

    it('updateNode modifies node properties', async () => {
      let capturedBody;
      server.use(
        http.patch(`${API_URL}/session/:sessionId/nodes/:nodeId`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json(mockDiagram);
        })
      );

      await updateNode('session-123', 'api-1', { label: 'Updated API' });

      expect(capturedBody).toEqual({ label: 'Updated API' });
    });
  });

  describe('Edge CRUD operations', () => {
    const testEdge = {
      id: 'new-edge-1',
      source: 'api-1',
      target: 'db-1',
      label: 'Direct connection',
    };

    it('addEdge adds an edge and returns updated diagram', async () => {
      const result = await addEdge('session-123', testEdge);

      expect(result.edges).toContainEqual(testEdge);
    });

    it('deleteEdge removes edge and returns updated diagram', async () => {
      const result = await deleteEdge('session-123', 'edge-1');

      expect(result.edges.find(e => e.id === 'edge-1')).toBeUndefined();
    });
  });

  describe('Group operations', () => {
    it('createNodeGroup merges nodes into a group', async () => {
      const result = await createNodeGroup('session-123', ['api-1', 'service-1']);

      expect(result.group_id).toBe('group-1');
      expect(result.diagram.nodes.find(n => n.id === 'group-1')).toBeDefined();
    });

    it('ungroupNodes dissolves a group', async () => {
      const result = await ungroupNodes('session-123', 'group-1');

      expect(result).toEqual(mockDiagram);
    });

    it('toggleGroupCollapse toggles collapse state', async () => {
      const result = await toggleGroupCollapse('session-123', 'group-1');

      expect(result).toEqual(mockDiagram);
    });
  });

  describe('Design Document operations', () => {
    it('generateDesignDoc starts generation', async () => {
      const result = await generateDesignDoc('session-123');

      expect(result.status).toBe('started');
    });

    it('generateDesignDoc includes diagram image when provided', async () => {
      let capturedBody;
      server.use(
        http.post(`${API_URL}/session/:sessionId/design-doc/generate`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ status: 'started' });
        })
      );

      await generateDesignDoc('session-123', 'base64-image-data');

      expect(capturedBody.diagram_image).toBe('base64-image-data');
    });

    it('getDesignDocStatus returns current status', async () => {
      const result = await getDesignDocStatus('session-123');

      expect(result.status).toBe('completed');
      expect(result.design_doc).toContain('Design Document');
    });

    it('pollDesignDocStatus polls until completed', async () => {
      let callCount = 0;
      server.use(
        http.get(`${API_URL}/session/:sessionId/design-doc/status`, () => {
          callCount++;
          if (callCount < 2) {
            return HttpResponse.json({ status: 'generating' });
          }
          return HttpResponse.json({
            status: 'completed',
            design_doc: '# Doc',
            duration_seconds: 30,
          });
        })
      );

      const result = await pollDesignDocStatus('session-123');

      expect(result.success).toBe(true);
      expect(result.design_doc).toBe('# Doc');
    });

    it('pollDesignDocStatus returns failure on error', async () => {
      server.use(
        http.get(`${API_URL}/session/:sessionId/design-doc/status`, () => {
          return HttpResponse.json({
            status: 'failed',
            error: 'AI service unavailable',
          });
        })
      );

      const result = await pollDesignDocStatus('session-123');

      expect(result.success).toBe(false);
      expect(result.error).toBe('AI service unavailable');
    });

    it('updateDesignDoc saves content', async () => {
      let capturedBody;
      server.use(
        http.patch(`${API_URL}/session/:sessionId/design-doc`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ success: true });
        })
      );

      await updateDesignDoc('session-123', '# Updated Doc');

      expect(capturedBody.content).toBe('# Updated Doc');
    });

    it('exportDesignDoc returns file data', async () => {
      const result = await exportDesignDoc('session-123', 'pdf', 'base64-image');

      expect(result.pdf).toBeDefined();
      expect(result.pdf.filename).toBe('design-document.pdf');
    });
  });

  describe('User Sessions operations', () => {
    it('getUserSessions returns user session list', async () => {
      const result = await getUserSessions();

      expect(result).toEqual(mockUserSessions);
      expect(result.length).toBe(2);
    });

    it('renameSession updates session name', async () => {
      const result = await renameSession('session-123', 'New Name');

      expect(result.success).toBe(true);
      expect(result.name).toBe('New Name');
    });

    it('deleteSession removes session', async () => {
      const result = await deleteSession('session-123');

      expect(result.success).toBe(true);
    });
  });

  describe('Authentication', () => {
    it('setClerkTokenGetter configures token injection', async () => {
      const mockGetToken = vi.fn().mockResolvedValue('mock-jwt-token');
      setClerkTokenGetter(mockGetToken);

      // Make a request - token should be added to headers
      let capturedHeaders;
      server.use(
        http.get(`${API_URL}/session/:sessionId`, ({ request }) => {
          capturedHeaders = Object.fromEntries(request.headers.entries());
          return HttpResponse.json(mockSession);
        })
      );

      await getSession('test-123');

      expect(mockGetToken).toHaveBeenCalled();
      expect(capturedHeaders.authorization).toBe('Bearer mock-jwt-token');
    });
  });

  describe('Error Handling', () => {
    it('handles 401 unauthorized error', async () => {
      server.use(
        http.get(`${API_URL}/session/:sessionId`, () => {
          return new HttpResponse(null, { status: 401 });
        })
      );

      await expect(getSession('test-123')).rejects.toThrow();
    });

    it('handles 403 forbidden error', async () => {
      server.use(
        http.get(`${API_URL}/session/:sessionId`, () => {
          return new HttpResponse(null, { status: 403 });
        })
      );

      await expect(getSession('test-123')).rejects.toThrow();
    });

    it('handles 500 server error with retries', async () => {
      server.use(
        http.get(`${API_URL}/session/:sessionId`, () => {
          return new HttpResponse(null, { status: 500 });
        })
      );

      // 500 errors trigger retries with exponential backoff
      await expect(getSession('test-123')).rejects.toThrow();
    }, 20000); // Longer timeout for retry tests

    it('handles network errors with retries', async () => {
      server.use(
        http.get(`${API_URL}/session/:sessionId`, () => {
          return HttpResponse.error();
        })
      );

      await expect(getSession('test-123')).rejects.toThrow();
    }, 20000); // Longer timeout for retry tests
  });

  describe('Retry Logic', () => {
    it('retries on 503 status code', async () => {
      let callCount = 0;
      server.use(
        http.get(`${API_URL}/session/:sessionId`, () => {
          callCount++;
          if (callCount < 2) {
            return new HttpResponse(null, { status: 503 });
          }
          return HttpResponse.json(mockSession);
        })
      );

      const result = await getSession('test-123');

      expect(callCount).toBe(2);
      expect(result.session_id).toBe('test-session-123');
    }, 10000);

    it('respects max retries limit', async () => {
      let callCount = 0;
      server.use(
        http.get(`${API_URL}/session/:sessionId`, () => {
          callCount++;
          return new HttpResponse(null, { status: 503 });
        })
      );

      await expect(getSession('test-123')).rejects.toThrow();

      // Initial request + 3 retries = 4 total
      expect(callCount).toBe(4);
    }, 20000); // Longer timeout for retry tests
  });
});

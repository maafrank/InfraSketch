/**
 * MSW (Mock Service Worker) request handlers
 * Intercepts network requests at the service worker level for production-like testing
 */

import { http, HttpResponse } from 'msw';

const API_URL = 'http://localhost:8000/api';

// Sample mock data
export const mockDiagram = {
  nodes: [
    {
      id: 'api-1',
      type: 'api',
      label: 'API Gateway',
      description: 'Main entry point for requests',
      inputs: [],
      outputs: ['service-1'],
      metadata: { technology: 'Kong' },
      position: { x: 0, y: 0 },
    },
    {
      id: 'service-1',
      type: 'service',
      label: 'User Service',
      description: 'Handles user authentication',
      inputs: ['api-1'],
      outputs: ['db-1'],
      metadata: { technology: 'Node.js' },
      position: { x: 200, y: 0 },
    },
    {
      id: 'db-1',
      type: 'database',
      label: 'PostgreSQL',
      description: 'Primary database',
      inputs: ['service-1'],
      outputs: [],
      metadata: { technology: 'PostgreSQL' },
      position: { x: 400, y: 0 },
    },
  ],
  edges: [
    { id: 'edge-1', source: 'api-1', target: 'service-1', label: 'HTTP' },
    { id: 'edge-2', source: 'service-1', target: 'db-1', label: 'SQL' },
  ],
};

export const mockSession = {
  session_id: 'test-session-123',
  user_id: 'test-user-id',
  diagram: mockDiagram,
  messages: [
    { role: 'user', content: 'Create a user authentication system' },
    { role: 'assistant', content: 'I\'ve created a basic user authentication system with an API Gateway, User Service, and PostgreSQL database.' },
  ],
  design_doc: null,
  name: 'User Auth System',
  name_generated: true,
  created_at: new Date().toISOString(),
};

export const mockUserSessions = [
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
];

// Default handlers - can be overridden in individual tests
export const handlers = [
  // Generate diagram (starts async generation)
  http.post(`${API_URL}/generate`, () => {
    return HttpResponse.json({
      session_id: 'test-session-123',
      status: 'generating',
    });
  }),

  // Diagram status polling
  http.get(`${API_URL}/session/:sessionId/diagram/status`, () => {
    return HttpResponse.json({
      status: 'completed',
      diagram: mockDiagram,
      messages: mockSession.messages,
      name: 'Test Diagram',
      duration_seconds: 5.2,
    });
  }),

  // Chat message
  http.post(`${API_URL}/chat`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      response: `I understand you want to ${body.message}. Here's my response.`,
      diagram: mockDiagram,
    });
  }),

  // Get session
  http.get(`${API_URL}/session/:sessionId`, ({ params }) => {
    return HttpResponse.json({
      ...mockSession,
      session_id: params.sessionId,
    });
  }),

  // Create blank session
  http.post(`${API_URL}/session/create-blank`, () => {
    return HttpResponse.json({
      session_id: 'new-blank-session',
      diagram: { nodes: [], edges: [] },
    });
  }),

  // Add node
  http.post(`${API_URL}/session/:sessionId/nodes`, async ({ request }) => {
    const node = await request.json();
    return HttpResponse.json({
      ...mockDiagram,
      nodes: [...mockDiagram.nodes, node],
    });
  }),

  // Delete node
  http.delete(`${API_URL}/session/:sessionId/nodes/:nodeId`, ({ params }) => {
    return HttpResponse.json({
      ...mockDiagram,
      nodes: mockDiagram.nodes.filter(n => n.id !== params.nodeId),
      edges: mockDiagram.edges.filter(
        e => e.source !== params.nodeId && e.target !== params.nodeId
      ),
    });
  }),

  // Update node
  http.patch(`${API_URL}/session/:sessionId/nodes/:nodeId`, async ({ params, request }) => {
    const updates = await request.json();
    return HttpResponse.json({
      ...mockDiagram,
      nodes: mockDiagram.nodes.map(n =>
        n.id === params.nodeId ? { ...n, ...updates } : n
      ),
    });
  }),

  // Add edge
  http.post(`${API_URL}/session/:sessionId/edges`, async ({ request }) => {
    const edge = await request.json();
    return HttpResponse.json({
      ...mockDiagram,
      edges: [...mockDiagram.edges, edge],
    });
  }),

  // Delete edge
  http.delete(`${API_URL}/session/:sessionId/edges/:edgeId`, ({ params }) => {
    return HttpResponse.json({
      ...mockDiagram,
      edges: mockDiagram.edges.filter(e => e.id !== params.edgeId),
    });
  }),

  // Create node group
  http.post(`${API_URL}/session/:sessionId/groups`, async ({ request }) => {
    const { child_node_ids } = await request.json();
    const groupNode = {
      id: 'group-1',
      type: 'group',
      label: 'Service Group',
      description: 'Grouped services',
      is_group: true,
      is_collapsed: true,
      child_ids: child_node_ids,
      position: { x: 100, y: 100 },
    };
    return HttpResponse.json({
      diagram: {
        ...mockDiagram,
        nodes: [...mockDiagram.nodes, groupNode],
      },
      group_id: 'group-1',
    });
  }),

  // Ungroup nodes
  http.delete(`${API_URL}/session/:sessionId/groups/:groupId`, () => {
    return HttpResponse.json(mockDiagram);
  }),

  // Toggle group collapse
  http.patch(`${API_URL}/session/:sessionId/groups/:groupId/collapse`, () => {
    return HttpResponse.json(mockDiagram);
  }),

  // Generate node description
  http.post(`${API_URL}/session/:sessionId/nodes/:nodeId/generate-description`, () => {
    return HttpResponse.json({
      description: 'AI-generated description for this component',
      diagram: mockDiagram,
    });
  }),

  // Design doc generation (starts async)
  http.post(`${API_URL}/session/:sessionId/design-doc/generate`, () => {
    return HttpResponse.json({
      status: 'started',
      message: 'Design document generation started',
    });
  }),

  // Design doc status
  http.get(`${API_URL}/session/:sessionId/design-doc/status`, () => {
    return HttpResponse.json({
      status: 'completed',
      design_doc: '# Design Document\n\nThis is a test design document.',
      duration_seconds: 30.5,
    });
  }),

  // Update design doc
  http.patch(`${API_URL}/session/:sessionId/design-doc`, () => {
    return HttpResponse.json({
      success: true,
    });
  }),

  // Export design doc
  http.post(`${API_URL}/session/:sessionId/design-doc/export`, () => {
    return HttpResponse.json({
      pdf: {
        content: 'base64-encoded-pdf-content',
        filename: 'design-document.pdf',
      },
    });
  }),

  // Get user sessions
  http.get(`${API_URL}/user/sessions`, () => {
    return HttpResponse.json(mockUserSessions);
  }),

  // Rename session
  http.patch(`${API_URL}/session/:sessionId/name`, async ({ request }) => {
    const { name } = await request.json();
    return HttpResponse.json({
      success: true,
      name,
    });
  }),

  // Delete session
  http.delete(`${API_URL}/session/:sessionId`, () => {
    return HttpResponse.json({
      success: true,
      message: 'Session deleted',
    });
  }),
];

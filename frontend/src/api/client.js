import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : 'http://localhost:8000/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const generateDiagram = async (prompt) => {
  const response = await client.post('/generate', { prompt });
  return response.data;
};

export const sendChatMessage = async (sessionId, message, nodeId = null) => {
  const response = await client.post('/chat', {
    session_id: sessionId,
    message,
    node_id: nodeId,
  });
  return response.data;
};

export const getSession = async (sessionId) => {
  const response = await client.get(`/session/${sessionId}`);
  return response.data;
};

export const addNode = async (sessionId, node) => {
  const response = await client.post(`/session/${sessionId}/nodes`, node);
  return response.data;
};

export const deleteNode = async (sessionId, nodeId) => {
  const response = await client.delete(`/session/${sessionId}/nodes/${nodeId}`);
  return response.data;
};

export const updateNode = async (sessionId, nodeId, node) => {
  const response = await client.patch(`/session/${sessionId}/nodes/${nodeId}`, node);
  return response.data;
};

export const addEdge = async (sessionId, edge) => {
  const response = await client.post(`/session/${sessionId}/edges`, edge);
  return response.data;
};

export const deleteEdge = async (sessionId, edgeId) => {
  const response = await client.delete(`/session/${sessionId}/edges/${edgeId}`);
  return response.data;
};

export const generateDesignDoc = async (sessionId, diagramImage = null) => {
  const response = await client.post(
    `/session/${sessionId}/design-doc/generate`,
    {
      diagram_image: diagramImage
    }
  );
  return response.data;
};

export const updateDesignDoc = async (sessionId, content) => {
  const response = await client.patch(
    `/session/${sessionId}/design-doc`,
    {
      content
    }
  );
  return response.data;
};

export const getDesignDocStatus = async (sessionId) => {
  const response = await client.get(`/session/${sessionId}/design-doc/status`);
  return response.data;
};

export const pollDesignDocStatus = async (sessionId, onProgress = null, maxWaitTime = 180000) => {
  const startTime = Date.now();
  const pollInterval = 2000; // Poll every 2 seconds

  while (Date.now() - startTime < maxWaitTime) {
    const status = await getDesignDocStatus(sessionId);

    // Call progress callback if provided
    if (onProgress) {
      onProgress(status);
    }

    // Check if completed
    if (status.status === 'completed') {
      return {
        success: true,
        design_doc: status.design_doc,
        duration: status.duration_seconds,
      };
    }

    // Check if failed
    if (status.status === 'failed') {
      return {
        success: false,
        error: status.error,
      };
    }

    // Still generating, wait before next poll
    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }

  // Timeout
  return {
    success: false,
    error: 'Design document generation timed out',
  };
};

export const exportDesignDoc = async (sessionId, format = 'pdf', diagramImage = null) => {
  const response = await client.post(
    `/session/${sessionId}/design-doc/export?format=${format}`,
    {
      diagram_image: diagramImage
    }
  );
  return response.data;
};

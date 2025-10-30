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

export const exportDesignDoc = async (sessionId, format = 'pdf', diagramImage = null) => {
  const response = await client.post(
    `/session/${sessionId}/export/design-doc?format=${format}`,
    {
      diagram_image: diagramImage
    }
  );
  return response.data;
};

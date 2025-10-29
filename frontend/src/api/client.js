import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

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

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : 'http://localhost:8000/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000, // 45 seconds (API Gateway times out at 30s)
});

// Store getToken function - will be set by App.jsx
let getClerkToken = null;

export const setClerkTokenGetter = (tokenGetter) => {
  getClerkToken = tokenGetter;
};

// Request interceptor to add Clerk auth token
client.interceptors.request.use(
  async (config) => {
    if (getClerkToken) {
      try {
        const token = await getClerkToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      } catch (error) {
        console.error('Failed to get Clerk token:', error);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error('Authentication required - please sign in');
      // The error will be caught by the calling code
    } else if (error.response?.status === 403) {
      console.error('Access denied - you don\'t have permission for this resource');
    }
    return Promise.reject(error);
  }
);

export const generateDiagram = async (prompt, model = null) => {
  const response = await client.post('/generate', { prompt, model });
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

export const getUserSessions = async () => {
  const response = await client.get('/user/sessions');
  return response.data;
};

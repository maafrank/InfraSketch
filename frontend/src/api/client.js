import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : 'http://localhost:8000/api';

// Retry configuration
const RETRY_CONFIG = {
  maxRetries: 3,
  baseDelayMs: 1000, // Start with 1 second
  maxDelayMs: 10000, // Cap at 10 seconds
  // Network errors that should trigger a retry
  retryableErrors: [
    'ERR_NETWORK',
    'ERR_NETWORK_CHANGED',
    'ECONNABORTED',
    'ETIMEDOUT',
    'ECONNRESET',
    'ENOTFOUND',
  ],
  // HTTP status codes that should trigger a retry
  retryableStatuses: [408, 429, 500, 502, 503, 504],
};

/**
 * Calculate delay with exponential backoff and jitter
 */
const getRetryDelay = (attempt) => {
  const exponentialDelay = RETRY_CONFIG.baseDelayMs * Math.pow(2, attempt);
  const jitter = Math.random() * 500; // Add up to 500ms of random jitter
  return Math.min(exponentialDelay + jitter, RETRY_CONFIG.maxDelayMs);
};

/**
 * Check if an error is retryable
 */
const isRetryableError = (error) => {
  // Network errors (no response received)
  if (!error.response) {
    return RETRY_CONFIG.retryableErrors.includes(error.code);
  }
  // HTTP errors with retryable status codes
  return RETRY_CONFIG.retryableStatuses.includes(error.response.status);
};

/**
 * Sleep for a given number of milliseconds
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

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

// Response interceptor with retry logic for transient errors
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;

    // Initialize retry count if not set
    config.__retryCount = config.__retryCount || 0;

    // Check if we should retry
    if (isRetryableError(error) && config.__retryCount < RETRY_CONFIG.maxRetries) {
      config.__retryCount += 1;

      const delay = getRetryDelay(config.__retryCount - 1);
      console.log(
        `Network error (${error.code || error.response?.status}), retrying in ${Math.round(delay)}ms... ` +
        `(attempt ${config.__retryCount}/${RETRY_CONFIG.maxRetries})`
      );

      // Wait before retrying
      await sleep(delay);

      // Retry the request
      return client.request(config);
    }

    // Log final error after all retries exhausted
    if (config.__retryCount > 0) {
      console.error(`Request failed after ${config.__retryCount} retries:`, error.message);
    }

    // Handle specific error types
    if (error.response?.status === 401) {
      console.error('Authentication required - please sign in');
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

export const getDiagramStatus = async (sessionId) => {
  const response = await client.get(`/session/${sessionId}/diagram/status`);
  return response.data;
};

/**
 * Poll diagram generation status until completed or failed.
 *
 * @param {string} sessionId - Session ID to poll
 * @param {function} onProgress - Optional callback for progress updates (receives status object)
 * @param {number} maxWaitTime - Max time to wait in milliseconds (default: 5 minutes)
 * @returns {Promise<{success: boolean, diagram?: object, messages?: array, name?: string, error?: string}>}
 */
export const pollDiagramStatus = async (sessionId, onProgress = null, maxWaitTime = 300000) => {
  const startTime = Date.now();
  const pollInterval = 2000; // Poll every 2 seconds

  while (Date.now() - startTime < maxWaitTime) {
    const status = await getDiagramStatus(sessionId);

    // Call progress callback if provided
    if (onProgress) {
      onProgress(status);
    }

    // Check if completed
    if (status.status === 'completed') {
      return {
        success: true,
        diagram: status.diagram,
        messages: status.messages,
        name: status.name,
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
    error: 'Diagram generation timed out after 5 minutes',
  };
};

export const sendChatMessage = async (sessionId, message, nodeId = null, model = null) => {
  const response = await client.post('/chat', {
    session_id: sessionId,
    message,
    node_id: nodeId,
    model,
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

export const renameSession = async (sessionId, name) => {
  const response = await client.patch(`/session/${sessionId}/name`, { name });
  return response.data;
};

export const deleteSession = async (sessionId) => {
  const response = await client.delete(`/session/${sessionId}`);
  return response.data;
};

export const createBlankSession = async () => {
  const response = await client.post('/session/create-blank');
  return response.data;
};

export const createNodeGroup = async (sessionId, childNodeIds, generateAI = true) => {
  const response = await client.post(`/session/${sessionId}/groups?generate_ai_description=${generateAI}`, {
    child_node_ids: childNodeIds
  });
  return response.data;
};

export const generateNodeDescription = async (sessionId, nodeId) => {
  const response = await client.post(`/session/${sessionId}/nodes/${nodeId}/generate-description`);
  return response.data;
};

export const toggleGroupCollapse = async (sessionId, groupId) => {
  const response = await client.patch(`/session/${sessionId}/groups/${groupId}/collapse`);
  return response.data;
};

export const ungroupNodes = async (sessionId, groupId) => {
  const response = await client.delete(`/session/${sessionId}/groups/${groupId}`);
  return response.data;
};

/**
 * Poll session to wait for name generation to complete.
 * Background task generates name after diagram creation.
 *
 * @param {string} sessionId - Session ID to poll
 * @param {function} onUpdate - Callback when name is generated (receives session name)
 * @param {number} maxWaitTime - Max time to wait in milliseconds (default: 10 seconds)
 * @returns {Promise<{success: boolean, name: string | null}>}
 */
export const pollSessionName = async (sessionId, onUpdate = null, maxWaitTime = 10000) => {
  const startTime = Date.now();
  const pollInterval = 1000; // Poll every 1 second

  while (Date.now() - startTime < maxWaitTime) {
    try {
      const session = await getSession(sessionId);

      // Check if name has been generated (not "Untitled Design" and name_generated is true)
      if (session.name && session.name !== 'Untitled Design' && session.name_generated !== false) {
        console.log('Session name generated:', session.name);
        if (onUpdate) {
          onUpdate(session.name);
        }
        return {
          success: true,
          name: session.name,
        };
      }
    } catch (error) {
      console.error('Error polling session name:', error);
      // Continue polling even on error (session might not be saved yet)
    }

    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }

  // Timeout - return whatever name we have (might be null or "Untitled Design")
  console.log('Session name polling timed out');
  return {
    success: false,
    name: null,
  };
};

/**
 * Generic poller for the backend's "start async task / poll status" pattern.
 *
 * Replaces the three near-identical poll functions for diagram generation,
 * design-doc generation, and repo analysis. They all loop on a status
 * endpoint until status is "completed" or "failed", with the only real
 * differences being the timeout and which result fields to extract.
 *
 * Usage:
 *   const poll = createPoller({
 *     fetchStatus: getDiagramStatus,
 *     timeoutMs: POLL_CONFIG.diagram.timeoutMs,
 *     mapSuccess: (s) => ({ diagram: s.diagram, messages: s.messages, ... }),
 *     timeoutMessage: 'Diagram generation timed out after 5 minutes',
 *   });
 *   const result = await poll(sessionId, onProgress);
 *
 * @param {object} config
 * @param {function} config.fetchStatus - async (sessionId) => statusObject
 * @param {function} config.mapSuccess - (status) => fields to merge into success result
 * @param {string} config.timeoutMessage - error message when maxWaitTime expires
 * @param {number} [config.timeoutMs=300000] - default timeout for the returned poller
 * @param {number} [config.intervalMs=2000] - poll interval
 * @returns async (sessionId, onProgress?, maxWaitTime?) => { success, ...mapped fields | error }
 */
export const createPoller = ({
  fetchStatus,
  mapSuccess,
  timeoutMessage,
  timeoutMs = 300000,
  intervalMs = 2000,
}) => {
  return async (sessionId, onProgress = null, maxWaitTime = timeoutMs) => {
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitTime) {
      const status = await fetchStatus(sessionId);

      if (onProgress) {
        onProgress(status);
      }

      if (status.status === 'completed') {
        return { success: true, ...mapSuccess(status) };
      }

      if (status.status === 'failed') {
        return { success: false, error: status.error };
      }

      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }

    return { success: false, error: timeoutMessage };
  };
};

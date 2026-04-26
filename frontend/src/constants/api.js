/**
 * API client timing constants.
 *
 * Polling intervals + max-wait timeouts for the async-task endpoints
 * (diagram generation, design-doc generation, repo analysis, session-name
 * derivation). createPoller in api/poller.js wires these up.
 */

export const POLL_INTERVAL_MS = 2000;
export const SESSION_NAME_POLL_INTERVAL_MS = 1000;

/** Per-task max wait before the poller surfaces a timeout error. */
export const POLL_TIMEOUTS_MS = {
  diagram: 5 * 60 * 1000,         // 300_000
  designDoc: 3 * 60 * 1000,       // 180_000
  repoAnalysis: 5 * 60 * 1000,    // 300_000
  sessionName: 10 * 1000,
};

/** Default request timeout for the axios client. */
export const REQUEST_TIMEOUT_MS = 45 * 1000;

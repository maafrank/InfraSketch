/**
 * MSW server for Node.js environment (used in Vitest)
 */

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);

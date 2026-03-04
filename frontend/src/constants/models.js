/**
 * Centralized Claude model configuration for the frontend.
 *
 * When Anthropic releases new model versions, update ONLY this file
 * and backend/app/config/models.py.
 */

export const MODELS = {
  HAIKU: 'claude-haiku-4-5',
  SONNET: 'claude-sonnet-4-6',
  OPUS: 'claude-opus-4-6',
};

export const DEFAULT_MODEL = MODELS.HAIKU;

/**
 * Model options for dropdown selectors.
 */
export const MODEL_OPTIONS = [
  { id: MODELS.HAIKU, label: 'Speed', description: 'Fast & Economical' },
  { id: MODELS.SONNET, label: 'Power', description: 'Best Quality, 3x cost' },
  { id: MODELS.OPUS, label: 'Ultra', description: 'Premium, 5x cost' },
];

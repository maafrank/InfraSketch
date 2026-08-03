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
 *
 * `premium: true` marks the models sold as "Power model access" on the Pro
 * tier. Kept in sync with PREMIUM_MODEL_PLANS in backend/app/billing/credit_costs.py.
 */
export const MODEL_OPTIONS = [
  { id: MODELS.HAIKU, label: 'Speed', description: 'Fast & Economical' },
  { id: MODELS.SONNET, label: 'Power', description: 'Best Quality', premium: true },
  { id: MODELS.OPUS, label: 'Ultra', description: 'Premium', premium: true },
];

/** Plans entitled to the premium (Power / Ultra) models. */
export const PREMIUM_MODEL_PLANS = ['pro', 'enterprise'];

/**
 * Whether a model option should be shown as locked for the given plan.
 *
 * Only locks when the plan is known to be free. An unknown plan (still
 * loading, or signed out) stays unlocked so the selector doesn't flicker;
 * the backend enforces the real entitlement either way.
 */
export function isModelLocked(option, plan) {
  if (!option?.premium) return false;
  if (!plan) return false;
  return !PREMIUM_MODEL_PLANS.includes(plan);
}

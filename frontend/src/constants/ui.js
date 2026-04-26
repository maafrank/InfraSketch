/**
 * UI layout constants. Co-located here so the same value isn't duplicated
 * across half a dozen components and become a maintenance hazard.
 */

/** Viewport width at or below which we render the mobile layout (fullscreen
 *  modals, hidden controls, etc.). Mirror this in the App.css media queries
 *  if it ever changes. */
export const MOBILE_BREAKPOINT = 768;

/** Resizable side-panel sizing (px). */
export const PANEL_WIDTHS = {
  chat: { default: 400, min: 150, max: 1200 },
  designDoc: { default: 400, min: 150, max: 1200 },
  sessionHistory: { default: 300, min: 200, max: 600 },
};

/** React Flow fit-view padding by viewport. */
export const FIT_PADDING = {
  mobile: 0.05,
  desktop: 0.2,
};

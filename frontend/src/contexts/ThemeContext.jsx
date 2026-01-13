import { createContext } from 'react';

// Context is internal - not exported to avoid fast refresh issues
const ThemeContext = createContext();

// Check if we're in a browser environment (for SSR/prerendering safety)
const isBrowser = typeof window !== 'undefined';

// Provider component - Terminal theme is always dark
export default function ThemeProvider({ children }) {
  // Always dark theme - terminal aesthetic
  const theme = 'dark';

  // Apply theme to document on mount (for any legacy CSS that checks data-theme)
  if (isBrowser) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }

  // toggleTheme is a no-op now but kept for API compatibility
  const toggleTheme = () => {};

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

// Export context for useTheme hook (in separate file)
export { ThemeContext };

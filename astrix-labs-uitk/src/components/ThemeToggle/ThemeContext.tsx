'use client';

import { createContext, useContext, useEffect, useState } from 'react';

export type Theme = 'dark' | 'light';

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const DEFAULT_STORAGE_KEY = 'atelier.night';

export interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
}

export function ThemeProvider({
  children,
  defaultTheme = 'dark',
  storageKey = DEFAULT_STORAGE_KEY,
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(defaultTheme);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const stored = localStorage.getItem(storageKey);
    if (storageKey === DEFAULT_STORAGE_KEY) {
      setThemeState(stored === '0' ? 'light' : 'dark');
    } else {
      if (stored === 'light' || stored === 'dark') setThemeState(stored);
    }
  }, [storageKey]);

  useEffect(() => {
    if (!mounted) return;
    const isNight = theme === 'dark';
    document.body.classList.toggle('mode-night', isNight);
    document.documentElement.setAttribute('data-theme', theme);
    if (storageKey === DEFAULT_STORAGE_KEY) {
      localStorage.setItem(storageKey, isNight ? '1' : '0');
    } else {
      localStorage.setItem(storageKey, theme);
    }
  }, [theme, mounted, storageKey]);

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

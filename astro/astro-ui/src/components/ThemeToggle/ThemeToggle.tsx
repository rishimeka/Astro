'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import styles from './ThemeToggle.module.scss';

interface ThemeToggleProps {
  size?: 'sm' | 'md';
  showLabel?: boolean;
}

export default function ThemeToggle({ size = 'md', showLabel = false }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();
  const iconSize = size === 'sm' ? 16 : 20;

  return (
    <button
      className={`${styles.toggle} ${styles[size]}`}
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? (
        <Sun size={iconSize} />
      ) : (
        <Moon size={iconSize} />
      )}
      {showLabel && (
        <span className={styles.label}>
          {theme === 'dark' ? 'Light' : 'Dark'}
        </span>
      )}
    </button>
  );
}

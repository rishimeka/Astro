'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useSidebar } from './SidebarContext';
import styles from './Sidebar.module.scss';

export interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

export interface SidebarProps {
  /** Navigation items to display */
  navItems: NavItem[];
  /** Current pathname for active state determination */
  currentPath: string;
  /** Logo element to display */
  logo?: React.ReactNode;
  /** Custom Link component for framework-specific routing */
  LinkComponent?: React.ComponentType<{
    href: string;
    className?: string;
    onClick?: () => void;
    title?: string;
    children: React.ReactNode;
  }>;
}

export function Sidebar({
  navItems,
  currentPath,
  logo,
  LinkComponent = 'a' as unknown as React.ComponentType<{
    href: string;
    className?: string;
    onClick?: () => void;
    title?: string;
    children: React.ReactNode;
  }>,
}: SidebarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { isCollapsed, toggleCollapsed } = useSidebar();
  const Link = LinkComponent;

  const isActive = (href: string) => {
    if (href === '/') {
      return currentPath === '/';
    }
    return currentPath.startsWith(href);
  };

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        className={styles.hamburger}
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle navigation"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          {isOpen ? (
            <>
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </>
          ) : (
            <>
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </>
          )}
        </svg>
      </button>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className={styles.overlay}
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`${styles.sidebar} ${isOpen ? styles.open : ''} ${isCollapsed ? styles.collapsed : ''}`}>
        <div className={styles.header}>
          {!isCollapsed && logo && (
            <div className={styles.logo}>
              {logo}
            </div>
          )}
          <button
            className={styles.collapseToggle}
            onClick={toggleCollapsed}
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        <nav className={styles.nav}>
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navItem} ${isActive(item.href) ? styles.active : ''}`}
              onClick={() => setIsOpen(false)}
              title={isCollapsed ? item.label : undefined}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              {!isCollapsed && <span className={styles.navLabel}>{item.label}</span>}
            </Link>
          ))}
        </nav>
      </aside>
    </>
  );
}

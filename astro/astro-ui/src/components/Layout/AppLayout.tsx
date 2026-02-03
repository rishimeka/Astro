'use client';

import Sidebar, { SidebarProvider, useSidebar } from '@/components/Sidebar';
import styles from './AppLayout.module.scss';

interface AppLayoutProps {
  children: React.ReactNode;
}

function AppLayoutContent({ children }: AppLayoutProps) {
  const { isCollapsed } = useSidebar();

  return (
    <div className={styles.layout}>
      <Sidebar />
      <main className={`${styles.main} ${isCollapsed ? styles.mainCollapsed : ''}`}>
        {children}
      </main>
    </div>
  );
}

export default function AppLayout({ children }: AppLayoutProps) {
  return (
    <SidebarProvider>
      <AppLayoutContent>{children}</AppLayoutContent>
    </SidebarProvider>
  );
}

'use client';

import Sidebar from '@/components/Sidebar/Sidebar';
import { SidebarProvider, useSidebar } from '@/components/Sidebar/SidebarContext';
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

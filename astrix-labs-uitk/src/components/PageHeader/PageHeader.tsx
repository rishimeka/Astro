import { ArrowLeft } from 'lucide-react';
import styles from './PageHeader.module.scss';

export interface Breadcrumb {
  label: string;
  href?: string;
}

export interface PageHeaderProps {
  title: string;
  titleBadge?: React.ReactNode;
  subtitle?: React.ReactNode;
  meta?: React.ReactNode;
  actions?: React.ReactNode;
  breadcrumbs?: Breadcrumb[];
  backHref?: string;
  /** Custom Link component for framework-specific routing (e.g., Next.js Link) */
  LinkComponent?: React.ComponentType<{ href: string; className?: string; children: React.ReactNode }>;
}

export function PageHeader({
  title,
  titleBadge,
  subtitle,
  meta,
  actions,
  breadcrumbs,
  backHref,
  LinkComponent = 'a' as unknown as React.ComponentType<{ href: string; className?: string; children: React.ReactNode }>,
}: PageHeaderProps) {
  const Link = LinkComponent;

  return (
    <header className={styles.header}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className={styles.breadcrumbs}>
          {breadcrumbs.map((crumb, index) => (
            <span key={index} className={styles.breadcrumbItem}>
              {crumb.href ? (
                <Link href={crumb.href} className={styles.breadcrumbLink}>
                  {crumb.label}
                </Link>
              ) : (
                <span className={styles.breadcrumbCurrent}>{crumb.label}</span>
              )}
              {index < breadcrumbs.length - 1 && (
                <span className={styles.breadcrumbSeparator}>/</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className={styles.titleRow}>
        <div className={styles.titleGroup}>
          <div className={styles.titleWithBack}>
            {backHref && (
              <Link href={backHref} className={styles.backButton}>
                <ArrowLeft size={24} />
              </Link>
            )}
            <h1 className={styles.title}>{title}</h1>
            {titleBadge && <span className={styles.titleBadge}>{titleBadge}</span>}
          </div>
          {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
          {meta && <div className={styles.meta}>{meta}</div>}
        </div>
        {actions && <div className={styles.actions}>{actions}</div>}
      </div>
    </header>
  );
}

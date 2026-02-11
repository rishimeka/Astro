import Link from 'next/link';
import { PageHeader as BasePageHeader, Breadcrumb } from 'astrix-labs-uitk';

interface PageHeaderProps {
  title: string;
  titleBadge?: React.ReactNode;
  subtitle?: React.ReactNode;
  meta?: React.ReactNode;
  actions?: React.ReactNode;
  breadcrumbs?: Breadcrumb[];
  backHref?: string;
}

export default function PageHeader(props: PageHeaderProps) {
  return <BasePageHeader {...props} LinkComponent={Link} />;
}

'use client';

import PageHeader from '@/components/PageHeader';
import StarCreator from '@/components/StarCreator';

export default function NewStarPage() {
  return (
    <div>
      <PageHeader
        title="Create Star"
        subtitle="Configure a new star from a directive with probes and custom settings"
        breadcrumbs={[
          { label: 'Stars', href: '/stars' },
          { label: 'New' },
        ]}
      />
      <StarCreator />
    </div>
  );
}

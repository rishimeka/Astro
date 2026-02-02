'use client';

import PageHeader from '@/components/PageHeader/PageHeader';
import DirectiveWizard from '@/components/DirectiveWizard';

export default function NewDirectivePage() {
  return (
    <div>
      <PageHeader
        title="Create Directive"
        subtitle="Build a new directive with template variables and probe references"
        breadcrumbs={[
          { label: 'Directives', href: '/directives' },
          { label: 'New' },
        ]}
      />
      <DirectiveWizard />
    </div>
  );
}

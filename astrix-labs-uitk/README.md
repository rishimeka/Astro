# astrix-labs-uitk

Astrix Labs UI Toolkit - A reusable design system with React components and SCSS styles.

## Installation

```bash
npm install astrix-labs-uitk
```

## Requirements

- React 18 or 19
- A bundler that supports SCSS (e.g., Next.js, Vite with sass)
- For Next.js: Add to `transpilePackages` in your config

### Next.js Setup

```ts
// next.config.ts
const nextConfig = {
  transpilePackages: ['astrix-labs-uitk'],
};
```

## Usage

### Import Styles

Add the design system styles to your global stylesheet:

```scss
// globals.scss or globals.css
@use 'astrix-labs-uitk/styles';
```

### Import Components

```tsx
import {
  DataTable,
  StatusBadge,
  Pagination,
  EmptyState,
  SearchInput,
  PageHeader,
  Sidebar,
  ThemeToggle,
  Spinner,
  PageLoader,
  SkeletonLoader,
  ErrorBoundary,
  ErrorMessage,
  ErrorPage,
  Markdown,
  MetadataPanel,
} from 'astrix-labs-uitk';
```

## Components

### DataTable

A sortable, paginated data table with loading states.

```tsx
import { DataTable, Column } from 'astrix-labs-uitk';

const columns: Column<User>[] = [
  { key: 'name', header: 'Name', sortable: true },
  { key: 'email', header: 'Email' },
];

<DataTable
  data={users}
  columns={columns}
  loading={isLoading}
  onRowClick={(row) => console.log(row)}
  onSort={(column, direction) => handleSort(column, direction)}
/>
```

### StatusBadge

Displays status with color-coded indicators.

```tsx
import { StatusBadge } from 'astrix-labs-uitk';

<StatusBadge status="running" />
<StatusBadge status="completed" size="sm" />
```

Supported statuses: `running`, `completed`, `failed`, `pending`, `awaiting_confirmation`, `cancelled`

### Pagination

Page navigation with size selector.

```tsx
import { Pagination } from 'astrix-labs-uitk';

<Pagination
  currentPage={1}
  totalPages={10}
  pageSize={25}
  totalItems={250}
  onPageChange={(page) => setPage(page)}
  onPageSizeChange={(size) => setPageSize(size)}
/>
```

### EmptyState

Placeholder for empty content areas.

```tsx
import { EmptyState } from 'astrix-labs-uitk';

<EmptyState
  icon={<SearchIcon />}
  title="No results found"
  description="Try adjusting your search criteria"
  action={{ label: 'Clear filters', onClick: clearFilters }}
/>
```

### SearchInput

Debounced search input with clear button.

```tsx
import { SearchInput } from 'astrix-labs-uitk';

<SearchInput
  value={search}
  onChange={setSearch}
  placeholder="Search..."
  debounceMs={300}
/>
```

### PageHeader

Page title with breadcrumbs and actions.

```tsx
import { PageHeader } from 'astrix-labs-uitk';
import Link from 'next/link';

<PageHeader
  title="Users"
  subtitle="Manage your team members"
  breadcrumbs={[
    { label: 'Home', href: '/' },
    { label: 'Users' },
  ]}
  actions={<button>Add User</button>}
  LinkComponent={Link}
/>
```

### Sidebar

Navigation sidebar with collapse functionality.

```tsx
import { Sidebar, SidebarProvider } from 'astrix-labs-uitk';
import Link from 'next/link';

const navItems = [
  { label: 'Dashboard', href: '/', icon: <DashboardIcon /> },
  { label: 'Users', href: '/users', icon: <UsersIcon /> },
];

<SidebarProvider>
  <Sidebar
    navItems={navItems}
    currentPath={pathname}
    logo={<Logo />}
    LinkComponent={Link}
  />
</SidebarProvider>
```

### ThemeToggle

Dark/light mode toggle button.

```tsx
import { ThemeToggle, ThemeProvider } from 'astrix-labs-uitk';

<ThemeProvider>
  <ThemeToggle size="md" showLabel />
</ThemeProvider>
```

### Loading Components

```tsx
import { Spinner, PageLoader, SkeletonLoader } from 'astrix-labs-uitk';

<Spinner size="md" />
<PageLoader message="Loading data..." />
<SkeletonLoader width="100%" height="20px" variant="text" />
```

### Error Components

```tsx
import { ErrorBoundary, ErrorMessage, ErrorPage } from 'astrix-labs-uitk';

<ErrorBoundary fallback={<ErrorPage message="Something went wrong" />}>
  <App />
</ErrorBoundary>

<ErrorMessage message="Failed to load" onRetry={refetch} />
```

### Markdown

Renders markdown with GitHub Flavored Markdown support.

```tsx
import { Markdown } from 'astrix-labs-uitk';

<Markdown>{`# Hello World\n\nThis is **bold** text.`}</Markdown>
```

### MetadataPanel

Displays key-value metadata with nested object support.

```tsx
import { MetadataPanel } from 'astrix-labs-uitk';

<MetadataPanel
  title="Details"
  metadata={{
    id: '123',
    status: 'active',
    config: { timeout: 30 },
  }}
/>
```

## Design Tokens

The package includes CSS custom properties for theming:

```scss
:root {
  --accent-primary: #6C72FF;
  --bg-primary: #0D1117;
  --text-primary: #FFFFFF;
  --font-body: 'Outfit', sans-serif;
  --font-display: 'Libre Baskerville', serif;
  --font-mono: 'JetBrains Mono', monospace;
  // ... and more
}
```

Light mode is supported via `[data-theme="light"]` attribute on the root element.

## License

MIT

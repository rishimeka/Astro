# Astro UI

The frontend application for Astro - an AI-powered workflow automation platform. Built with Next.js 16, React 19, and TypeScript.

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **React**: 19.2 with React Compiler enabled
- **Styling**: SCSS with CSS custom properties (design tokens)
- **Graph Editor**: React Flow for constellation builder
- **Icons**: Lucide React
- **Markdown**: react-markdown with GFM support

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run production server
npm start

# Run linting
npm run lint
```

The app runs at http://localhost:3000

## Folder Structure

```
astro-ui/
├── src/
│   ├── app/                      # Next.js App Router pages
│   │   ├── layout.tsx           # Root layout with fonts, theme
│   │   ├── page.tsx             # Home page (redirects to launchpad)
│   │   ├── not-found.tsx        # 404 page
│   │   ├── design-system/       # Design system preview
│   │   ├── launchpad/           # Chat interface
│   │   ├── constellations/      # Workflow management
│   │   │   ├── page.tsx         # List view
│   │   │   ├── new/             # Create constellation
│   │   │   └── [id]/            # Detail & edit views
│   │   ├── stars/               # Star (execution unit) management
│   │   │   ├── page.tsx
│   │   │   ├── new/
│   │   │   └── [id]/
│   │   ├── directives/          # Directive (prompt) management
│   │   │   ├── page.tsx
│   │   │   ├── new/
│   │   │   └── [id]/
│   │   ├── probes/              # Tool registry (read-only)
│   │   │   ├── page.tsx
│   │   │   └── [name]/
│   │   ├── runs/                # Execution history
│   │   │   ├── page.tsx
│   │   │   ├── new/
│   │   │   └── [id]/
│   │   └── styles/              # Global SCSS
│   │       ├── tokens.scss      # Design tokens
│   │       ├── globals.scss     # Base styles
│   │       └── components.scss  # Reusable component styles
│   │
│   ├── components/              # React components
│   │   ├── Chat/               # Launchpad chat interface
│   │   │   ├── index.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   ├── ChatMessage.tsx
│   │   │   ├── ExecutionProgress.tsx
│   │   │   └── StreamingIndicator.tsx
│   │   ├── ConstellationBuilder/ # React Flow graph editor
│   │   ├── ConstellationCard/   # Card for list views
│   │   ├── DirectiveWizard/     # Step-by-step directive creation
│   │   ├── StarCreator/         # Star creation form
│   │   ├── Execution/           # Run visualization components
│   │   ├── Layout/              # App layout wrapper
│   │   ├── Sidebar/             # Navigation sidebar
│   │   ├── DataTable/           # Sortable data tables
│   │   ├── Pagination/          # Page navigation
│   │   ├── Loading/             # Spinners, skeletons
│   │   ├── Error/               # Error states
│   │   ├── EmptyState/          # Empty list states
│   │   ├── SearchInput/         # Search with debounce
│   │   ├── TagFilter/           # Tag-based filtering
│   │   ├── StatusFilter/        # Status filtering
│   │   ├── DateRangeFilter/     # Date range picker
│   │   ├── StatusBadge/         # Status indicators
│   │   ├── PageHeader/          # Page titles with actions
│   │   ├── ContentViewer/       # Directive content display
│   │   ├── MetadataPanel/       # Metadata display
│   │   ├── Markdown/            # Markdown renderer
│   │   ├── ThemeToggle/         # Dark/light mode
│   │   ├── DeleteConfirmModal/  # Deletion confirmation
│   │   └── VariableInput/       # Template variable inputs
│   │
│   ├── hooks/                   # Custom React hooks
│   │   ├── useChat.ts          # Chat/conversation state
│   │   ├── useConstellations.ts # Constellation CRUD
│   │   ├── useDirectives.ts    # Directive CRUD
│   │   ├── useStars.ts         # Star CRUD
│   │   ├── useRuns.ts          # Run management
│   │   ├── useProbes.ts        # Probe listing
│   │   └── useExecutionStream.ts # SSE streaming
│   │
│   ├── lib/                     # Utilities
│   │   ├── api/                # API client
│   │   │   ├── client.ts       # Fetch wrapper
│   │   │   ├── endpoints.ts    # API URL constants
│   │   │   ├── sse.ts          # SSE connection handler
│   │   │   └── types.ts        # API error types
│   │   └── utils/              # Helper functions
│   │
│   ├── context/                 # React contexts
│   │   └── ThemeContext.tsx    # Theme provider
│   │
│   └── types/                   # TypeScript definitions
│       └── astro.ts            # All Astro domain types
│
├── public/                      # Static assets
│   └── fonts/                  # Custom fonts
│
├── .claude/                     # Claude Code configuration
│   └── docs/
│       └── DESIGN_SYSTEM.md    # Design token reference
│
└── scripts/                     # Build scripts
```

## Pages Overview

| Route | Description |
|-------|-------------|
| `/` | Home - redirects to Launchpad |
| `/launchpad` | Chat interface for triggering workflows |
| `/constellations` | List all workflow graphs |
| `/constellations/new` | Create new constellation |
| `/constellations/[id]` | View constellation details |
| `/constellations/[id]/edit` | Edit constellation in graph editor |
| `/stars` | List all execution units |
| `/stars/new` | Create new star |
| `/stars/[id]` | View star details |
| `/directives` | List all prompt templates |
| `/directives/new` | Create new directive |
| `/directives/[id]` | View/edit directive |
| `/probes` | List available tools |
| `/probes/[name]` | View probe details |
| `/runs` | Execution history |
| `/runs/[id]` | Run details & status |
| `/design-system` | Design token preview |

## Key Components

### Launchpad Chat

The main user interface. Users describe tasks in natural language, and the system:
1. Matches to appropriate constellation
2. Collects required variables through conversation
3. Executes the workflow
4. Streams results back

```tsx
import { Chat } from '@/components/Chat';

<Chat />
```

### Constellation Builder

Visual graph editor built on React Flow for creating and editing constellations.

Features:
- Drag-and-drop node placement
- Auto-layout with dagre
- Edge creation with validation
- Node property editing
- Zoom and pan controls

```tsx
import { ConstellationBuilder } from '@/components/ConstellationBuilder';

<ConstellationBuilder
  constellation={constellation}
  stars={availableStars}
  onChange={handleChange}
/>
```

### Execution Stream

Real-time visualization of constellation execution using Server-Sent Events.

```tsx
import { useExecutionStream } from '@/hooks';

const { status, nodeOutputs, error } = useExecutionStream(runId);
```

## Custom Hooks

### Data Fetching

```tsx
// Constellations
const { constellations, loading, createConstellation } = useConstellations();

// Directives
const { directives, getDirective, updateDirective } = useDirectives();

// Stars
const { stars, createStar, deleteStar } = useStars();

// Runs
const { runs, startRun, confirmRun } = useRuns();

// Probes
const { probes, loading } = useProbes();
```

### Chat State

```tsx
const {
  messages,
  isLoading,
  pendingConstellation,
  sendMessage,
  confirmExecution,
} = useChat();
```

## Design System

The UI uses a comprehensive token-based design system. Key tokens:

### Colors

```scss
// Primary accent
--accent-primary: #4A9DEA;
--accent-secondary: #A78BFA;

// Backgrounds
--bg-primary: #0D1117;
--bg-secondary: #161B22;
--bg-tertiary: #21262D;

// Text
--text-primary: #E6EDF3;
--text-secondary: #8B949E;

// Status
--status-success: #3FB950;
--status-warning: #D29922;
--status-error: #F85149;
```

### Typography

```scss
// Fonts
--font-display: 'Libre Baskerville', serif;  // Headlines
--font-body: 'Outfit', sans-serif;           // Body text
--font-mono: 'JetBrains Mono', monospace;    // Code

// Sizes
--font-size-xs: 0.75rem;
--font-size-sm: 0.875rem;
--font-size-base: 1rem;
--font-size-lg: 1.125rem;
--font-size-xl: 1.25rem;
```

### Component Classes

```scss
// Buttons
.btn.btn-primary.btn-md

// Inputs
.input, .textarea, .select

// Cards
.card, .card-header, .card-body

// Status badges
.badge.badge-success
```

See `.claude/docs/DESIGN_SYSTEM.md` for complete reference.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL |
| `NEXT_PUBLIC_USE_MOCK` | `false` | Use mock data (no backend) |

## API Integration

The frontend communicates with the FastAPI backend:

```typescript
// Base API client
import { api } from '@/lib/api';

// Typed endpoints
const constellations = await api.get<Constellation[]>('/constellations');
const run = await api.post<Run>(`/constellations/${id}/run`, { variables });
```

SSE for real-time updates:

```typescript
import { createSSEConnection } from '@/lib/api/sse';

const connection = createSSEConnection(`/runs/${runId}/stream`);
connection.onMessage((event) => {
  // Handle node_started, node_completed, run_completed, etc.
});
```

## TypeScript Types

All backend models are mirrored in `src/types/astro.ts`:

- `Directive`, `DirectiveSummary`, `DirectiveCreate`
- `Star`, `StarSummary`, `StarCreate` (and specific types)
- `Constellation`, `ConstellationSummary`, `ConstellationCreate`
- `Run`, `RunSummary`, `NodeOutput`
- `Probe`
- SSE event types

## Development Notes

### React Compiler

The React Compiler is enabled, providing automatic memoization. **Do not use**:
- `useMemo`
- `useCallback`
- `React.memo`

The compiler handles optimization automatically.

### Styling Convention

Always use CSS custom properties:

```scss
// Good
.component {
  background: var(--bg-secondary);
  color: var(--text-primary);
  padding: var(--spacing-md);
}

// Bad
.component {
  background: #161B22;
  color: #E6EDF3;
  padding: 16px;
}
```

### Mobile Responsiveness

Breakpoint at 768px:

```scss
.component {
  display: grid;
  grid-template-columns: repeat(3, 1fr);

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}
```

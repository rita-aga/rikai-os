# Plan: RikaiOS Web UI Implementation

**Status**: COMPLETED
**Created**: 2026-01-10 18:00
**Sequence**: 002

## Goal

Build the web UI for RikaiOS - a glassmorphic, Japanese-minimalist dashboard that connects to the REST API.

## Context

- Backend API exists at `src/rikai/servers/api.py` (FastAPI on port 8000)
- Web app location: `rikai-apps/apps/web/` (currently empty)
- Monorepo uses pnpm + Turbo
- Must follow STYLING.md strictly: borderless, glassmorphic, emerald accent (#10B981), no shadcn/Tailwind defaults

## Vision Alignment Checklist

- [ ] Borderless design (NO bold outlines)
- [ ] Glassmorphism with backdrop blur
- [ ] Emerald green accent (#10B981)
- [ ] Japanese minimalism (Kanso, Ma - negative space)
- [ ] Magazine-inspired typography (Inter font)
- [ ] Light/dark mode support
- [ ] Proactive but not intrusive UX
- [ ] Transparency over magic (show sources)

---

## Options & Decisions

### Framework Choice

| Option | Pros | Cons |
|--------|------|------|
| **React + Vite** | Fast builds, familiar to team, used in rikai-code | Boilerplate, state management needed |
| Solid.js | Smaller, more performant | Less ecosystem, team unfamiliar |
| Svelte | Clean syntax, built-in reactivity | Different paradigm |

**Decision**: React + Vite
**Reasoning**: Consistency with rikai-code CLI, largest ecosystem, team familiarity
**Trade-off**: Accept bundle size overhead for developer experience

### Styling Approach

| Option | Pros | Cons |
|--------|------|------|
| **CSS Variables + Custom CSS** | Full control, matches STYLING.md vision | More manual work |
| Tailwind (heavily customized) | Utility classes, fast | STYLING.md explicitly says NO Tailwind defaults |
| CSS-in-JS (styled-components) | Scoped, dynamic | Runtime overhead, breaks from guidelines |

**Decision**: CSS Variables + Custom CSS Modules
**Reasoning**: STYLING.md requires custom styling, CSS variables enable theming, no dependencies
**Trade-off**: More CSS to write but full control over visual language

### State Management

| Option | Pros | Cons |
|--------|------|------|
| React Query + Context | Server state handled well, minimal boilerplate | Two patterns to learn |
| **Zustand** | Simple, lightweight, single pattern | Less caching built-in |
| Redux Toolkit | Powerful, full-featured | Overkill for this size |

**Decision**: Zustand + React Query
**Reasoning**: Zustand for client state (theme, UI), React Query for server state (entities, search)
**Trade-off**: Two libraries but clean separation of concerns

---

## Quick Decision Log

| Time | Decision | Rationale | Trade-off |
|------|----------|-----------|-----------|
| 18:00 | React + Vite | Consistency with existing TS code | Bundle size |
| 18:00 | Custom CSS | STYLING.md compliance | More manual work |
| 18:00 | Zustand + React Query | Clean state separation | Two patterns |
| 18:00 | Lucide icons | Mentioned in STYLING.md | Need to customize |

---

## Phases

### Phase 1: Project Setup
- [ ] Initialize Vite + React + TypeScript in `apps/web`
- [ ] Configure pnpm workspace integration
- [ ] Set up CSS variables from STYLING.md
- [ ] Create base layout component
- [ ] Configure API client for backend (localhost:8000)

### Phase 2: Core Components
- [ ] Glass surface component (cards, panels)
- [ ] Borderless button variants (primary, ghost)
- [ ] Borderless input component
- [ ] Typography components (Display, H1-H3, Body, Caption)
- [ ] Theme provider (light/dark mode)

### Phase 3: Dashboard Layout
- [ ] Minimal navigation (icon-only sidebar)
- [ ] Main content area with bento grid
- [ ] Context panel (self, now, projects)
- [ ] Responsive layout

### Phase 4: Entity Views
- [ ] Entity list view (filterable by type)
- [ ] Entity detail view
- [ ] Entity create/edit forms
- [ ] Entity relationships visualization

### Phase 5: Search
- [ ] Semantic search bar
- [ ] Search results with highlighting
- [ ] Source citations (transparency)

### Phase 6: Tama Chat
- [ ] Chat interface
- [ ] Context citations in responses
- [ ] Proactive suggestions display

### Phase 7: Polish
- [ ] Animations (scroll reveals, transitions)
- [ ] Loading states (skeleton shimmer)
- [ ] Error handling (friendly messages)
- [ ] Accessibility (keyboard nav, screen reader)

---

## What to Try

### Works Now
- Backend API runs at localhost:8000
- Health check: `curl http://localhost:8000/health`
- Swagger docs: `http://localhost:8000/docs`

### Doesn't Work Yet
- Web UI doesn't exist (this plan)
- No frontend to test

### Known Limitations
- Tama chat requires Letta server
- Some connectors need external API keys

---

## Technical Specifications

### File Structure
```
rikai-apps/apps/web/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/
│   │   └── client.ts         # API client
│   ├── components/
│   │   ├── ui/               # Core UI components
│   │   │   ├── Surface.tsx
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   └── Typography.tsx
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   └── features/
│   │       ├── EntityList.tsx
│   │       ├── Search.tsx
│   │       └── Chat.tsx
│   ├── hooks/
│   │   └── useEntities.ts
│   ├── stores/
│   │   └── theme.ts
│   └── styles/
│       ├── variables.css     # CSS custom properties
│       ├── global.css        # Global styles
│       └── components/       # Component CSS modules
└── public/
    └── fonts/                # Inter font files
```

### API Integration

```typescript
// Base URL
const API_URL = 'http://localhost:8000'

// Key endpoints
GET /entities?type=<type>     // List entities
POST /entities                 // Create entity
GET /entities/:id             // Get entity
POST /search                  // Semantic search
GET /context                  // Get user context
POST /tama/chat               // Chat with Tama
```

### CSS Variables (from STYLING.md)

```css
:root {
  /* Colors */
  --color-accent: #10B981;
  --color-accent-hover: #059669;
  --color-background: #FAFAFA;
  --color-surface: rgba(255, 255, 255, 0.8);
  --color-text: #171717;
  --color-text-muted: #525252;

  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 48px;

  /* Radii */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-normal: 200ms ease;
}

[data-theme="dark"] {
  --color-background: #0A0A0A;
  --color-surface: rgba(23, 23, 23, 0.7);
  --color-text: #FAFAFA;
  --color-text-muted: #A3A3A3;
}
```

---

## Verification Checklist

- [ ] No shadcn or Tailwind defaults
- [ ] All buttons/inputs are borderless
- [ ] Glassmorphism working with backdrop-filter
- [ ] Emerald accent used correctly
- [ ] Light/dark mode switching works
- [ ] All API endpoints connecting
- [ ] No console errors
- [ ] Responsive on mobile
- [ ] Keyboard navigation works

---

## Instance Log

| Instance | Phase | Status | Notes |
|----------|-------|--------|-------|
| Main | 1 | In Progress | Starting setup |

---

## Notes

- IMPORTANT: STYLING.md says NO shadcn, NO Tailwind defaults
- Inter font is the primary font stack
- Animations should be under 300ms
- Keep UI "calm and premium", not busy

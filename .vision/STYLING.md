# RikaiOS Styling Guide

> Visual language, design principles, and UI/UX guidelines.

---

## Design Philosophy

**Stillness and clarity.** The visual language of RikaiOS reflects its philosophy — calm, intentional, and uncluttered.

The aesthetic draws from:
- **Japanese minimalism** — Kanso (simplicity), Ma (negative space)
- **Editorial design** — Magazine-inspired typography and layout
- **Liquid Glass** — Apple's 2025+ design language with depth and translucency

**Light doesn't mean white. Light means transparent.**

---

## Core Principles

### 1. Borderless Design
- **NO bold outlines** on forms, buttons, cards
- Use transparency, subtle gradients, and tone variations to create hierarchy
- Differentiate elements through background opacity, not borders
- Shadows should be soft and diffuse, never harsh

### 2. Transparency Over Solidity
- "Light and airy" achieved through transparency values, not white backgrounds
- Layer translucent elements to create depth
- Use backdrop blur (glassmorphism) for floating panels
- Variations in opacity create visual rhythm

### 3. Minimal Color Palette
- **2-3 accent colors maximum**, rest is base tones
- Most UI should be black/white/gray with accent highlights
- Color is intentional — used for emphasis, not decoration

### 4. Magazine-Inspired Layouts
- Editorial typography with clear hierarchy
- Generous whitespace (Ma — negative space)
- Content integrated with backgrounds, not floating on top
- Asymmetric compositions that feel designed, not templated

---

## Constraints (DO NOT)

### Forbidden Patterns
- ❌ **NO shadcn, Tailwind defaults**, or generic component libraries
- ❌ **NO bold borders/outlines** on buttons, inputs, cards
- ❌ **NO pastels** — colors should be fresh and vibrant
- ❌ **NO muddy/earthy tones** — keep it clean and crisp
- ❌ **NO heavy drop shadows** — use subtle, diffuse shadows only
- ❌ **NO cluttered layouts** — every element must earn its space
- ❌ **NO generic icon libraries** without customization

### Avoid
- Boxy, corporate-feeling layouts
- Excessive visual noise
- Animation for animation's sake
- Competing focal points

---

## RikaiOS Color Palette

### Primary Accent
```
Emerald Green (Fresh, not muddy)
- Primary:    #10B981 (Emerald 500)
- Hover:      #059669 (Emerald 600)
- Subtle:     #10B98120 (20% opacity)
- Glow:       #10B98140 (40% opacity for glows)
```

### Base Colors

**Light Mode:**
```
- Background:     #FAFAFA or #FFFFFF
- Surface:        #FFFFFF with 80-95% opacity
- Surface-alt:    #F5F5F5
- Text-primary:   #171717
- Text-secondary: #525252
- Text-muted:     #A3A3A3
```

**Dark Mode:**
```
- Background:     #0A0A0A or #000000
- Surface:        #171717 with 60-80% opacity
- Surface-alt:    #262626
- Text-primary:   #FAFAFA
- Text-secondary: #A3A3A3
- Text-muted:     #525252
```

### Usage Rules
- Emerald for: primary actions, highlights, active states, success
- Gray tones for: everything else
- Never more than 1-2 accent colors visible at once

---

## Typography

### Font Stack
```css
/* Primary - Clean, modern sans-serif */
font-family: 'Inter', 'SF Pro Display', -apple-system, sans-serif;

/* Mono - For code and data */
font-family: 'JetBrains Mono', 'SF Mono', monospace;
```

### Scale (Magazine-Inspired)
```
Display:    48-72px  (bold, tight tracking)
H1:         32-40px  (semibold)
H2:         24-28px  (medium)
H3:         18-20px  (medium)
Body:       15-16px  (regular, relaxed line-height)
Caption:    12-13px  (medium, slightly tracked)
```

### Guidelines
- Headlines can be bold and dramatic
- Body text should breathe — 1.5-1.7 line height
- Use font weight variations, not color, for hierarchy
- Tight tracking on large text, normal on body

---

## Components

### Cards & Surfaces
```css
/* Glassmorphism card */
.surface {
  background: rgba(255, 255, 255, 0.7);  /* light mode */
  background: rgba(23, 23, 23, 0.6);     /* dark mode */
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16-24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
}
```

### Buttons
```css
/* Primary button - no border, subtle gradient */
.button-primary {
  background: linear-gradient(135deg, #10B981, #059669);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 12px 24px;
  font-weight: 500;
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3);
  transition: all 0.2s ease;
}

/* Ghost button - transparent with subtle hover */
.button-ghost {
  background: transparent;
  color: currentColor;
  border: none;
  border-radius: 12px;
  padding: 12px 24px;
}
.button-ghost:hover {
  background: rgba(16, 185, 129, 0.1);
}
```

### Inputs
```css
/* Borderless input with subtle background */
.input {
  background: rgba(0, 0, 0, 0.04);  /* light mode */
  background: rgba(255, 255, 255, 0.06);  /* dark mode */
  border: none;
  border-radius: 12px;
  padding: 14px 18px;
  transition: background 0.2s ease;
}
.input:focus {
  background: rgba(16, 185, 129, 0.08);
  outline: none;
}
```

---

## Motion & Animation

### Principles (2026 Trends)
Based on [Motion UI Trends 2026](https://lomatechnology.com/blog/motion-ui-trends-2026/2911):

1. **Purposeful motion** — every animation serves UX, not decoration
2. **Spatial continuity** — transitions show where you came from
3. **Micro-interactions** — subtle feedback on every action
4. **Scroll storytelling** — content reveals as narrative

### Timing
```css
/* Keep transitions under 300ms for responsiveness */
--transition-fast: 150ms ease;
--transition-normal: 200ms ease;
--transition-slow: 300ms ease-out;

/* Easing */
--ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
```

### Allowed Animations
- **Page transitions** — crossfade or slide with shared element continuity
- **Scroll-triggered reveals** — subtle fade-up on entering viewport
- **Hover states** — scale (1.02-1.05), glow, or background shift
- **Loading states** — skeleton shimmer or subtle pulse
- **Parallax** — accent only, not on every element (see [best practices](https://www.promodo.com/blog/key-ux-ui-design-trends))

### Forbidden
- ❌ Bouncy/elastic animations (feels cheap)
- ❌ Long animations (>500ms)
- ❌ Animations that block interaction
- ❌ Parallax on mobile (disable or simplify)

---

## Layout Patterns

### Bento Grid
Inspired by [2026 UI trends](https://www.index.dev/blog/ui-ux-design-trends):
- Modular blocks of varying sizes
- Creates visual rhythm and hierarchy
- Good for dashboards and overview screens

### Floating Elements
From reference images:
- Organic shapes (circles, blobs) as containers
- Elements "float" with generous spacing
- Background integrates with content (not separate layers)

### Editorial Layouts
- Asymmetric compositions
- Large hero typography
- Full-bleed backgrounds that flow into content
- Column-based layouts with intentional breaks

---

## Dashboard Design

Based on [dashboard design principles](https://muz.li/blog/best-dashboard-design-examples-inspirations-for-2026/):

### Structure
```
┌─────────────────────────────────────────────────┐
│  Minimal nav (icons only, expand on hover)      │
├────────┬────────────────────────────────────────┤
│        │                                        │
│ Side   │  Main content area                     │
│ panel  │  - Bento grid for metrics              │
│ (opt)  │  - Cards with glassmorphism            │
│        │  - Generous whitespace                 │
│        │                                        │
└────────┴────────────────────────────────────────┘
```

### Metrics Display
- Large numbers with small labels
- Trend indicators (subtle, not flashy)
- Circular or organic containers (like Biosites reference)
- Sparklines over full charts when possible

### Data Visualization
- Minimal axis lines
- No gridlines unless essential
- Emerald green for positive, muted for neutral
- Tooltips on hover, not always visible

---

## Dark/Light Mode

Both modes should feel **equally premium**.

### Light Mode
- Not stark white — use off-whites (#FAFAFA, #F5F5F5)
- Subtle warm or cool tint acceptable
- Shadows more prominent
- Glassmorphism with light blur

### Dark Mode
- True blacks (#0A0A0A) or soft blacks (#171717)
- Surfaces slightly lighter than background
- Emerald accent pops more — use sparingly
- Glassmorphism with higher opacity surfaces

### Switching
- Respect system preference by default
- Allow manual override
- Transition between modes smoothly (200ms)

---

## Inspirations & References

### Aesthetic References (Mood, Not Color)
- **Biosites** — Floating organic shapes, airy metrics display
- **Duna** — Full-bleed editorial backgrounds, typography-forward
- **Superhuman** — Dark glassmorphism, premium feel, minimal chrome

### 2026 Trends to Embrace
Based on research from [UX Collective](https://uxdesign.cc/10-ux-design-shifts-you-cant-ignore-in-2026-8f0da1c6741d) and [Prototypr](https://blog.prototypr.io/ux-ui-design-trends-for-2026-from-ai-to-xr-to-vibe-creation-7c5f8e35dc1d):

- **Liquid Glass** — translucent, fluid surfaces
- **Micro-movements** — breathing elements, cursor proximity reactions
- **Scroll storytelling** — content unfolds as narrative
- **Hyper-personalization** — interface adapts to user context
- **Spatial continuity** — transitions maintain sense of place

### What Sets RikaiOS Apart
- Japanese-inspired calm (not Silicon Valley busy)
- Fresh emerald, not corporate blue
- Editorial elegance, not dashboard utility
- Borderless everything

---

## Implementation Notes

### CSS Variables
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

### Tech Recommendations
- **CSS** — Custom properties, native CSS (no Tailwind)
- **Animations** — Framer Motion or native CSS transitions
- **Icons** — Custom or Lucide (customized)
- **Charts** — Recharts or Visx (heavily styled)
- **Accessibility** — Radix UI primitives with custom styling

### Radix UI Primitives

Use **Radix UI** for accessible, unstyled component primitives. Radix provides robust keyboard navigation, focus management, and ARIA patterns out of the box — we just add our custom styling on top.

**Approved Radix packages:**
```
@radix-ui/react-dialog      # Modals
@radix-ui/react-dropdown-menu  # Menus
@radix-ui/react-tooltip     # Tooltips
@radix-ui/react-select      # Select dropdowns
@radix-ui/react-tabs        # Tab navigation
@radix-ui/react-popover     # Popovers
@radix-ui/react-switch      # Toggle switches
```

**Styling pattern:**
```css
/* Override all Radix default styling with our design system */
.DialogOverlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.DialogContent {
  background: var(--color-surface);
  backdrop-filter: blur(var(--blur-lg));
  border: none; /* NO borders */
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
}
```

**Key principles:**
1. Radix provides behavior, we provide 100% of the styling
2. Never use Radix's default styles — override everything
3. Keep our borderless, glassmorphic aesthetic
4. Radix is for accessibility, not for visual design

---

*The interface should feel like a calm, premium space — not a busy productivity tool.*

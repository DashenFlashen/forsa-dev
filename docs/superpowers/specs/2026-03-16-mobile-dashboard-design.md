# Mobile Dashboard Redesign

## Problem

The forsa-dev dashboard is built desktop-first and is difficult to use on a phone:

- The environment table has 7 columns that don't fit on a ~375px screen
- Action buttons (30px) are too small for touch interaction (44px minimum)
- Forms and health panel consume scroll space before you reach the environment list
- The terminal overlay doesn't account for mobile browser chrome (address bar)
- The header layout wraps awkwardly on narrow screens

## Scope

Targeted mobile adaptation. Desktop layout is unchanged. All changes are behind
responsive breakpoints (Tailwind `lg:` prefix as the desktop threshold, matching
the existing codebase convention).

## Design

### A. Environment cards on mobile

Replace the `<table>` with stacked cards below `lg` breakpoint.

**Card layout:**

```
+------------------------------------------+
| env-name                            [AN] |
| feature/my-branch                        |
| [running]  [attached]  3h 12m   :8081 -> |
| [play] [stop] [restart]  [term] [trash]  |
+------------------------------------------+
```

- Top row: environment name (left), user initials (right)
- Second row: branch name (only if different from env name), muted text
- Third row: server + tmux status badges (left), uptime + port link (right)
- Bottom row: action buttons with 44px touch targets

The table remains for `lg:` screens, unchanged.

**Implementation:** EnvironmentTable conditionally renders `<EnvironmentCard>`
components (wrapped in `lg:hidden`) and the existing `<table>` (wrapped in
`hidden lg:block`). Both are in the DOM; CSS controls visibility.

EnvironmentCard props mirror EnvironmentRow: `env`, `onAction`, `loadingAction`,
`onSelect`, `isSelected`, `onDelete`, `loadingDelete`.

### B. Collapsible sections on mobile

Health panel, "New Environment" form, and "Import Branch" form each become
collapsible on mobile. On desktop they remain always-open.

**Behavior:**
- Collapsed by default on mobile (below `lg`)
- Tap the section header to expand/collapse
- ChevronRight/ChevronDown icon indicates state
- On desktop (`lg:` and up), always expanded, no toggle affordance shown

**Implementation:** A `CollapsibleSection` component. Props: `title`, `children`.

Desktop override mechanism: the content wrapper uses
`hidden` + state-controlled toggle on mobile, plus `lg:!block` to force
visibility on desktop regardless of collapsed state. The toggle button itself
uses `lg:hidden` so it's invisible on desktop.

### C. Compact mobile header

**Mobile (< lg):**
- Reduce horizontal padding from `px-6` to `px-4 lg:px-6`
- Hide the hostname text on mobile (`hidden lg:inline`)
- Keep user name + switch link

**Desktop:** unchanged.

### D. Terminal overlay fixes

**Problem:** `fixed inset-0` uses implicit `100vh` which on mobile Safari/Chrome
includes the area behind the address bar, causing content to be cut off.

**Fix:** Replace `fixed inset-0` with `fixed inset-x-0 top-0 h-dvh` on the
mobile terminal overlay. `h-dvh` uses the dynamic viewport height which
accounts for the mobile browser chrome. Falls back to `vh` in older browsers.

**Toolbar on mobile:** The terminal toolbar currently shows icon + name +
status badge + tab buttons + spacer + port link + close button all in one row.
On mobile, this overflows. Fix:
- Hide the environment name and status badge on mobile (`hidden lg:inline`)
- Keep: tab buttons (left), port link + close button (right)
- Reduce padding: `px-4 py-2.5` -> `px-2 py-1.5 lg:px-4 lg:py-2.5`

### E. Touch-friendly action buttons

Increase button padding on mobile:
- Action buttons: `p-1.5` -> `p-2.5 lg:p-1.5`
- Terminal and delete buttons: same treatment
- Minimum 44x44px hit area on mobile

### F. Data dir field

Hide the data dir field behind a "more options" toggle in both forms.
It rarely changes and takes up space on every visit.

**Behavior:**
- Default: hidden, small "Options" link below the main input row
- Click to reveal the data dir input
- On desktop: same behavior (this is a usability improvement everywhere)

## Files to modify

| File | Change |
|------|--------|
| `dashboard/src/App.jsx` | Mobile header, collapsible wrappers, `h-dvh` on terminal overlay |
| `dashboard/src/components/EnvironmentTable.jsx` | Card layout for mobile, table for desktop |
| `dashboard/src/components/EnvironmentRow.jsx` | No changes needed — only visible on desktop (`hidden lg:block`) |
| `dashboard/src/components/EnvironmentCard.jsx` | **New** — mobile card for an environment |
| `dashboard/src/components/HealthPanel.jsx` | Wrap in collapsible on mobile |
| `dashboard/src/components/CreateEnvironment.jsx` | Collapsible wrapper, data dir toggle |
| `dashboard/src/components/ImportBranch.jsx` | Collapsible wrapper, data dir toggle |
| `dashboard/src/components/TerminalView.jsx` | Compact toolbar on mobile, responsive padding |
| `dashboard/src/components/ActionButtons.jsx` | Touch-sized button padding on mobile |
| `dashboard/src/components/CollapsibleSection.jsx` | **New** — reusable collapsible wrapper |

## Out of scope

- PWA / service worker / install-to-home
- Bottom navigation bar
- Swipe gestures
- Changes to the backend or ttyd configuration

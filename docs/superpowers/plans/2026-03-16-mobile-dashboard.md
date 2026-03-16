# Mobile Dashboard Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the forsa-dev dashboard usable on mobile phones (~375px screens).

**Architecture:** Targeted responsive adaptation using Tailwind breakpoints. Desktop layout unchanged. New components for mobile card layout and collapsible sections. All mobile-specific rendering gated behind `lg:` breakpoint (matching existing codebase convention).

**Tech Stack:** React 18, Tailwind CSS 3.4, lucide-react icons, Vite

**Spec:** `docs/superpowers/specs/2026-03-16-mobile-dashboard-design.md`

**Testing:** No frontend test framework exists. Verify changes visually using @test-ui after each task. Run `cd dashboard && npm run build` to catch compile errors.

---

## Chunk 1: Foundation Components

### Task 1: Create CollapsibleSection component

**Files:**
- Create: `dashboard/src/components/CollapsibleSection.jsx`

- [ ] **Step 1: Create the component**

```jsx
import { useState } from 'react'
import { ChevronRight } from 'lucide-react'

export default function CollapsibleSection({ title, children }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 px-5 py-4">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 lg:hidden"
      >
        <ChevronRight
          className={`h-3.5 w-3.5 text-gray-500 transition-transform ${open ? 'rotate-90' : ''}`}
        />
        <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          {title}
        </h2>
      </button>
      <h2 className="mb-3 hidden text-xs font-semibold uppercase tracking-wider text-gray-500 lg:block">
        {title}
      </h2>
      <div className={`${open ? '' : 'hidden'} lg:!block`}>
        {children}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify build**

Run: `cd /home/anders/repos/forsa-dev/dashboard && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/CollapsibleSection.jsx
git commit -m "feat: add CollapsibleSection component for mobile"
```

---

### Task 2: Create EnvironmentCard component

**Files:**
- Create: `dashboard/src/components/EnvironmentCard.jsx`
- Read: `dashboard/src/components/EnvironmentRow.jsx` (reference for props/logic)
- Read: `dashboard/src/components/StatusBadge.jsx` (reuse)
- Read: `dashboard/src/components/ActionButtons.jsx` (reuse)

The card replicates EnvironmentRow's functionality in a stacked mobile layout.
It shares the same props interface as EnvironmentRow.

- [ ] **Step 1: Create the component**

```jsx
import { useState } from 'react'
import { Terminal, Trash2 } from 'lucide-react'
import ActionButtons from './ActionButtons'
import ConfirmModal from './ConfirmModal'
import StatusBadge from './StatusBadge'

function UserInitials({ user }) {
  const initials = user
    .split(/[-_\s]/)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
  return (
    <span
      title={user}
      className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-gray-700 text-xs font-medium text-gray-300"
    >
      {initials}
    </span>
  )
}

export default function EnvironmentCard({ env, onAction, loadingAction, onSelect, isSelected, onDelete, loadingDelete }) {
  const [confirmDelete, setConfirmDelete] = useState(null)

  const handleDeleteClick = (e) => {
    e.stopPropagation()
    setConfirmDelete('normal')
  }

  const handleConfirmDelete = async () => {
    const force = confirmDelete === 'force'
    setConfirmDelete(null)
    try {
      await onDelete(env.user, env.name, force)
    } catch (e) {
      if (e.message.includes('409')) {
        setConfirmDelete('force')
      }
    }
  }

  const branchDiffers = env.branch !== env.name
  const ttydAlive = env.status.ttyd === 'alive'
  const ageMs = Date.now() - new Date(env.created_at).getTime()
  const terminalReady = ttydAlive && ageMs >= 10_000

  return (
    <>
      <div
        onClick={() => onSelect(env)}
        className={`rounded-lg border p-4 transition-colors ${
          isSelected
            ? 'border-blue-500 bg-gray-900'
            : 'border-gray-800 bg-gray-900/50 active:bg-gray-900'
        }`}
      >
        {/* Row 1: name + user */}
        <div className="flex items-center justify-between">
          <span className="font-mono text-sm font-medium text-gray-100">{env.name}</span>
          <UserInitials user={env.user} />
        </div>

        {/* Row 2: branch (if differs) */}
        {branchDiffers && (
          <div className="mt-0.5 font-mono text-xs text-gray-500">{env.branch}</div>
        )}

        {/* Row 3: status badges + uptime + port */}
        <div className="mt-3 flex items-center gap-2">
          <StatusBadge status={env.status.server} />
          <StatusBadge status={env.status.tmux} />
          <div className="flex-1" />
          <span className="text-xs text-gray-500 tabular-nums">{env.uptime}</span>
          <a
            href={env.url}
            target="_blank"
            rel="noreferrer"
            className="font-mono text-sm text-blue-400"
            onClick={(e) => e.stopPropagation()}
          >
            :{env.port}
          </a>
        </div>

        {/* Row 4: actions */}
        <div className="mt-3 flex items-center gap-2 border-t border-gray-800 pt-3" onClick={(e) => e.stopPropagation()}>
          <ActionButtons env={env} onAction={onAction} loading={loadingAction} />
          <div className="flex-1" />
          <button
            onClick={() => onSelect(env)}
            disabled={!terminalReady}
            title={!ttydAlive ? 'Terminal not available' : !terminalReady ? 'Terminal starting…' : 'Open terminal'}
            className={`rounded-md p-2.5 transition-colors ${
              terminalReady
                ? 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                : 'text-gray-600 cursor-not-allowed opacity-30'
            }`}
          >
            <Terminal className="h-4 w-4" />
          </button>
          <button
            onClick={handleDeleteClick}
            disabled={loadingDelete}
            title="Delete environment"
            className="rounded-md p-2.5 text-gray-500 transition-colors hover:bg-red-900/40 hover:text-red-400 disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {confirmDelete === 'normal' && (
        <ConfirmModal
          title={`Delete "${env.name}"?`}
          message="This will stop the server, remove the tmux session, and delete the git worktree."
          confirmLabel="Delete"
          danger
          onConfirm={handleConfirmDelete}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
      {confirmDelete === 'force' && (
        <ConfirmModal
          title="Branch not pushed — force delete?"
          message={`Branch '${env.branch}' has unpushed commits. Force delete will permanently discard them.`}
          confirmLabel="Force delete"
          danger
          onConfirm={handleConfirmDelete}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </>
  )
}
```

- [ ] **Step 2: Verify build**

Run: `cd /home/anders/repos/forsa-dev/dashboard && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/EnvironmentCard.jsx
git commit -m "feat: add EnvironmentCard component for mobile layout"
```

---

## Chunk 2: Integrate Mobile Components

### Task 3: Update EnvironmentTable with mobile card view

**Files:**
- Modify: `dashboard/src/components/EnvironmentTable.jsx`

Show cards on mobile (`lg:hidden`), table on desktop (`hidden lg:block`).

- [ ] **Step 1: Add EnvironmentCard import and card list**

Add import at top of `EnvironmentTable.jsx`:
```jsx
import EnvironmentCard from './EnvironmentCard'
```

Replace the return block (after the empty state check) with:

```jsx
  return (
    <>
      {/* Mobile: card layout */}
      <div className="flex flex-col gap-3 lg:hidden">
        {envs.map((env) => (
          <EnvironmentCard
            key={`${env.user}-${env.name}`}
            env={env}
            onAction={onAction}
            loadingAction={loadingActions[`${env.user}/${env.name}`]}
            onSelect={onSelect}
            isSelected={selectedEnv?.user === env.user && selectedEnv?.name === env.name}
            onDelete={onDelete}
            loadingDelete={!!loadingDeletes[`${env.user}/${env.name}`]}
          />
        ))}
      </div>

      {/* Desktop: table layout */}
      <div className="hidden overflow-x-auto rounded-lg border border-gray-800 lg:block">
        <table className="w-full text-left">
          <thead className="bg-gray-900 text-xs uppercase tracking-wider text-gray-500">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">User</th>
              <th className="px-4 py-3 font-medium">Server</th>
              <th className="px-4 py-3 font-medium">Tmux</th>
              <th className="px-4 py-3 font-medium">Port</th>
              <th className="px-4 py-3 font-medium">Uptime</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {envs.map((env) => (
              <EnvironmentRow
                key={`${env.user}-${env.name}`}
                env={env}
                onAction={onAction}
                loadingAction={loadingActions[`${env.user}/${env.name}`]}
                onSelect={onSelect}
                isSelected={selectedEnv?.user === env.user && selectedEnv?.name === env.name}
                onDelete={onDelete}
                loadingDelete={!!loadingDeletes[`${env.user}/${env.name}`]}
              />
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
```

- [ ] **Step 2: Verify build**

Run: `cd /home/anders/repos/forsa-dev/dashboard && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/EnvironmentTable.jsx
git commit -m "feat: show environment cards on mobile, table on desktop"
```

---

### Task 4: Make CreateEnvironment collapsible with data dir toggle

**Files:**
- Modify: `dashboard/src/components/CreateEnvironment.jsx`

- [ ] **Step 1: Wrap form in CollapsibleSection, add data dir toggle**

Replace the outer `<div>` wrapper and `<h2>` with `CollapsibleSection`.
Add a `showOptions` state to toggle the data dir field.

Full updated component:

```jsx
import { useEffect, useState } from 'react'
import { Plus, RefreshCw } from 'lucide-react'
import CollapsibleSection from './CollapsibleSection'

export default function CreateEnvironment({ onCreate, defaultDataDir }) {
  const [name, setName] = useState('')
  const [dataDir, setDataDir] = useState('')
  const [loading, setLoading] = useState(false)
  const [showOptions, setShowOptions] = useState(false)

  useEffect(() => {
    if (defaultDataDir && !dataDir) setDataDir(defaultDataDir)
  }, [defaultDataDir])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    try {
      await onCreate(name.trim(), 'main', dataDir.trim() || null)
      setName('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <CollapsibleSection title="New Environment">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <div className="flex flex-wrap gap-2">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Name (e.g. ticket-42)"
            className="flex-1 min-w-48 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
          />
          <button
            type="submit"
            disabled={loading || !name.trim()}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
          >
            {loading ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Plus className="h-3.5 w-3.5" />
            )}
            {loading ? 'Creating…' : 'Create'}
          </button>
        </div>
        {showOptions ? (
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500 whitespace-nowrap w-16">Data dir</label>
            <input
              type="text"
              value={dataDir}
              onChange={(e) => setDataDir(e.target.value)}
              placeholder="/data/dev"
              className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm font-mono text-gray-300 placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
            />
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setShowOptions(true)}
            className="self-start text-xs text-gray-500 hover:text-gray-400"
          >
            Options…
          </button>
        )}
      </form>
    </CollapsibleSection>
  )
}
```

- [ ] **Step 2: Verify build**

Run: `cd /home/anders/repos/forsa-dev/dashboard && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/CreateEnvironment.jsx
git commit -m "feat: make CreateEnvironment collapsible, hide data dir behind toggle"
```

---

### Task 5: Make ImportBranch collapsible with data dir toggle

**Files:**
- Modify: `dashboard/src/components/ImportBranch.jsx`

Same pattern as Task 4.

- [ ] **Step 1: Wrap in CollapsibleSection, add data dir toggle**

Full updated component:

```jsx
import { useEffect, useState } from 'react'
import { Download, RefreshCw } from 'lucide-react'
import CollapsibleSection from './CollapsibleSection'

const NAME_RE = /^[a-z0-9][a-z0-9_-]*$/

function deriveName(branch) {
  return branch.split('/').pop().toLowerCase().replace(/[^a-z0-9_-]/g, '-').replace(/^-+/, '')
}

export default function ImportBranch({ onCreate, defaultDataDir }) {
  const [branches, setBranches] = useState([])
  const [branch, setBranch] = useState('')
  const [name, setName] = useState('')
  const [dataDir, setDataDir] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingBranches, setLoadingBranches] = useState(true)
  const [showOptions, setShowOptions] = useState(false)

  useEffect(() => {
    fetch('/api/branches')
      .then((r) => r.json())
      .then((d) => { setBranches(d.branches); setLoadingBranches(false) })
      .catch(() => setLoadingBranches(false))
  }, [])

  useEffect(() => {
    if (defaultDataDir && !dataDir) setDataDir(defaultDataDir)
  }, [defaultDataDir])

  function handleBranchChange(e) {
    const b = e.target.value
    setBranch(b)
    setName(b ? deriveName(b) : '')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!branch || !name.trim()) return
    setLoading(true)
    try {
      await onCreate(name.trim(), 'main', dataDir.trim() || null, branch)
      setBranch('')
      setName('')
    } finally {
      setLoading(false)
    }
  }

  const nameValid = NAME_RE.test(name)

  return (
    <CollapsibleSection title="Import Branch">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <div className="flex flex-wrap gap-2">
          <select
            value={branch}
            onChange={handleBranchChange}
            disabled={loadingBranches}
            className="flex-1 min-w-48 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 disabled:opacity-50"
          >
            <option value="">{loadingBranches ? 'Loading…' : 'Select branch…'}</option>
            {branches.map((b) => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Environment name"
            className={`flex-1 min-w-32 rounded-md border px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 ${
              name && !nameValid
                ? 'border-red-500 bg-gray-800 focus:ring-red-500/50'
                : 'border-gray-700 bg-gray-800 focus:border-blue-500 focus:ring-blue-500/50'
            }`}
          />
          <button
            type="submit"
            disabled={loading || !branch || !nameValid}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
          >
            {loading
              ? <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              : <Download className="h-3.5 w-3.5" />}
            {loading ? 'Importing…' : 'Import'}
          </button>
        </div>
        {showOptions ? (
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500 whitespace-nowrap w-16">Data dir</label>
            <input
              type="text"
              value={dataDir}
              onChange={(e) => setDataDir(e.target.value)}
              placeholder="/data/dev"
              className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm font-mono text-gray-300 placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
            />
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setShowOptions(true)}
            className="self-start text-xs text-gray-500 hover:text-gray-400"
          >
            Options…
          </button>
        )}
      </form>
    </CollapsibleSection>
  )
}
```

- [ ] **Step 2: Verify build**

Run: `cd /home/anders/repos/forsa-dev/dashboard && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/ImportBranch.jsx
git commit -m "feat: make ImportBranch collapsible, hide data dir behind toggle"
```

---

### Task 6: Make HealthPanel collapsible

**Files:**
- Modify: `dashboard/src/components/HealthPanel.jsx`

- [ ] **Step 1: Wrap in CollapsibleSection**

```jsx
import CollapsibleSection from './CollapsibleSection'

function Gauge({ label, value, max, unit }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0
  const color =
    pct > 85 ? 'bg-red-500' :
    pct > 60 ? 'bg-yellow-500' :
    'bg-green-500'

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-400">{label}</span>
        <span className="text-xs tabular-nums text-gray-300">
          {value.toFixed(1)} / {max.toFixed(1)} {unit}
          <span className="ml-2 text-gray-500">({pct}%)</span>
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-gray-700">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default function HealthPanel({ health }) {
  if (!health) return null
  return (
    <CollapsibleSection title="System Health">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Gauge label={`CPU (${health.cpu_count} cores)`} value={health.cpu_percent} max={100} unit="%" />
        <Gauge label="RAM" value={health.ram_used_gb} max={health.ram_total_gb} unit="GB" />
        <Gauge label="Disk" value={health.disk_used_gb} max={health.disk_total_gb} unit="GB" />
      </div>
    </CollapsibleSection>
  )
}
```

- [ ] **Step 2: Verify build**

Run: `cd /home/anders/repos/forsa-dev/dashboard && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/HealthPanel.jsx
git commit -m "feat: make HealthPanel collapsible on mobile"
```

---

## Chunk 3: Terminal, Touch Targets, Header

### Task 7: Compact TerminalView toolbar on mobile

**Files:**
- Modify: `dashboard/src/components/TerminalView.jsx`

- [ ] **Step 1: Update toolbar for mobile**

Hide the env name, terminal icon, and status badge on mobile. Reduce padding.
The `ml-2` on the tab buttons div is intentionally removed since the hidden
elements no longer need the extra spacing.

Replace the toolbar `<div>` (the one with `border-b`) with:

```jsx
      <div className="flex items-center gap-2 border-b border-gray-800 bg-gray-900 px-2 py-1.5 lg:gap-3 lg:px-4 lg:py-2.5 shrink-0">
        <Terminal className="hidden h-4 w-4 shrink-0 text-gray-500 lg:block" />
        <span className="hidden font-mono text-sm font-medium text-gray-100 lg:inline">{env.name}</span>
        <span className="hidden lg:inline"><StatusBadge status={env.status.server} /></span>
        <div className="flex gap-1">
          {['terminal', 'logs'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded px-2.5 py-1 text-xs font-medium capitalize transition-colors ${
                tab === t
                  ? 'bg-gray-700 text-gray-100'
                  : 'text-gray-500 hover:bg-gray-800 hover:text-gray-300'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <a
          href={env.url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1 rounded px-2 py-1 text-xs text-blue-400 hover:bg-gray-800 hover:text-blue-300 transition-colors"
          onClick={(e) => e.stopPropagation()}
        >
          :{env.port}
          <ExternalLink className="h-3 w-3" />
        </a>
        <button
          onClick={onClose}
          className="rounded p-2 text-gray-500 hover:bg-gray-800 hover:text-gray-200 transition-colors lg:p-1"
          aria-label="Close terminal"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
```

- [ ] **Step 2: Verify build**

Run: `cd /home/anders/repos/forsa-dev/dashboard && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/TerminalView.jsx
git commit -m "feat: compact TerminalView toolbar on mobile"
```

---

### Task 8: Touch-friendly ActionButtons

**Files:**
- Modify: `dashboard/src/components/ActionButtons.jsx`

- [ ] **Step 1: Increase button padding and icon size on mobile**

In the `ActionBtn` component, make three changes:

1. Button className — change:
   `rounded-md p-1.5 transition-colors disabled:opacity-50 ${colorClass}`
   to:
   `rounded-md p-2.5 lg:p-1.5 transition-colors disabled:opacity-50 ${colorClass}`

2. Icon className — change:
   `<Icon className="h-3.5 w-3.5" />`
   to:
   `<Icon className="h-4 w-4 lg:h-3.5 lg:w-3.5" />`

3. Spinner className — change:
   `<RefreshCw className="h-3.5 w-3.5 animate-spin" />`
   to:
   `<RefreshCw className="h-4 w-4 lg:h-3.5 lg:w-3.5 animate-spin" />`

- [ ] **Step 2: Verify build**

Run: `cd /home/anders/repos/forsa-dev/dashboard && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/ActionButtons.jsx
git commit -m "feat: touch-friendly action button sizes on mobile"
```

---

### Task 9: Update App.jsx — header, terminal overlay, main padding

**Files:**
- Modify: `dashboard/src/App.jsx`

- [ ] **Step 1: Compact header on mobile**

In the `<header>` section, change:
- `px-6 py-4` → `px-4 py-3 lg:px-6 lg:py-4`
- Hide hostname on mobile: wrap the hostname `<span>` with `hidden lg:inline`

Replace the header `<div>`:
```jsx
          <div className="mx-auto max-w-7xl px-4 py-3 lg:px-6 lg:py-4 flex items-center gap-3">
            <span className="text-lg font-bold tracking-tight text-gray-100">forsa-dev</span>
            {health && (
              <span className="hidden text-xs text-gray-500 font-mono lg:inline">
                {host}
              </span>
            )}
            <div className="ml-auto flex items-center gap-2 text-sm text-gray-400">
              <span>
                logged in as <span className="font-medium text-gray-200 capitalize">{user}</span>
              </span>
              <button
                onClick={handleSwitchUser}
                className="text-blue-400 hover:text-blue-300 hover:underline"
              >
                switch
              </button>
            </div>
          </div>
```

- [ ] **Step 2: Reduce main padding on mobile**

Change `<main>` className:
```
px-6 py-6 → px-4 py-4 lg:px-6 lg:py-6
```

- [ ] **Step 3: Fix terminal overlay height**

Change the mobile terminal overlay `<div>` from:
```jsx
<div className="fixed inset-0 z-50 flex flex-col bg-gray-950 lg:hidden">
```
to:
```jsx
<div className="fixed inset-x-0 top-0 z-50 flex h-dvh flex-col bg-gray-950 lg:hidden">
```

- [ ] **Step 4: Verify build**

Run: `cd /home/anders/repos/forsa-dev/dashboard && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/App.jsx
git commit -m "feat: compact header, reduced padding, dvh terminal overlay on mobile"
```

---

## Chunk 4: Build and Visual Verification

### Task 10: Build production assets and verify

**Files:**
- Modify: `src/forsa_dev/dashboard/static/` (build output)

- [ ] **Step 1: Build production bundle**

Run: `cd /home/anders/repos/forsa-dev/dashboard && npm run build`
Expected: Build succeeds, output goes to `../src/forsa_dev/dashboard/static/`.

- [ ] **Step 2: Run linter**

Run: `cd /home/anders/repos/forsa-dev && uv run ruff check src/ tests/`
Expected: No errors.

- [ ] **Step 3: Run tests**

Run: `cd /home/anders/repos/forsa-dev && uv run pytest`
Expected: All tests pass.

- [ ] **Step 4: Visual verification**

Use @test-ui to verify the dashboard on both mobile (375px) and desktop (1280px)
viewports. Check:
- Cards show on mobile, table on desktop
- Collapsible sections work (collapsed by default on mobile, expanded on desktop)
- Terminal overlay fills the full mobile viewport
- Touch targets are at least 44px
- Data dir toggle works
- Header is compact on mobile

- [ ] **Step 5: Commit built assets**

```bash
git add src/forsa_dev/dashboard/static/
git commit -m "build: update dashboard production assets for mobile"
```

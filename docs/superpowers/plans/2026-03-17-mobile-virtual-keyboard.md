# Mobile Virtual Keyboard Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a virtual keyboard bar to the dashboard terminal that provides arrow keys, Esc, Tab, Ctrl+C, and PageUp/PageDown for mobile phone users.

**Architecture:** A single React component (`VirtualKeyboard.jsx`) renders below the ttyd iframe on touch devices. It opens a dedicated WebSocket to ttyd's binary protocol for sending keystrokes. CSS media query `(pointer: coarse)` controls visibility — desktop users never see it.

**Tech Stack:** React 18, Tailwind CSS, ttyd WebSocket binary protocol

**Spec:** `docs/superpowers/specs/2026-03-17-mobile-virtual-keyboard-design.md`

---

### File Structure

| File | Role |
|------|------|
| `dashboard/src/index.css` | Modify: add `touch-only` CSS class for `(pointer: coarse)` detection |
| `dashboard/src/components/VirtualKeyboard.jsx` | Create: virtual keyboard component with WebSocket logic, button layout, key repeat |
| `dashboard/src/components/TerminalView.jsx` | Modify: import and render VirtualKeyboard below iframe |

---

### Task 1: Add touch-only CSS class and create VirtualKeyboard component

**Files:**
- Modify: `dashboard/src/index.css`
- Create: `dashboard/src/components/VirtualKeyboard.jsx`

- [ ] **Step 1: Add touch-only CSS class to index.css**

Append to `dashboard/src/index.css` (after the existing `@tailwind` directives):

```css
.touch-only {
  display: none;
}
@media (pointer: coarse) {
  .touch-only {
    display: flex;
  }
}
```

No `!important` needed — the media query rule wins by source order when both selectors match.

- [ ] **Step 2: Create VirtualKeyboard.jsx**

```jsx
import { useEffect, useRef, useCallback, useState } from 'react'
import {
  ArrowUp, ArrowDown, ArrowLeft, ArrowRight,
  ChevronsUp, ChevronsDown
} from 'lucide-react'

const KEYS = [
  { label: 'Esc', value: '\x1b' },
  { label: 'Tab', value: '\t' },
  { icon: ArrowUp, value: '\x1b[A' },
  { icon: ArrowDown, value: '\x1b[B' },
  { icon: ArrowLeft, value: '\x1b[D' },
  { icon: ArrowRight, value: '\x1b[C' },
  { label: 'C-c', value: '\x03' },
  { icon: ChevronsUp, value: '\x1b[5~', title: 'Page Up' },
  { icon: ChevronsDown, value: '\x1b[6~', title: 'Page Down' },
]

const TTYD_INPUT_CMD = 0x00
const RECONNECT_DELAYS = [1000, 2000, 4000, 10000]
const KEY_REPEAT_INTERVAL = 100
const KEY_REPEAT_DELAY = 400
const encoder = new TextEncoder()

export default function VirtualKeyboard({ host, ttydPort }) {
  const wsRef = useRef(null)
  const retryRef = useRef(0)
  const retryTimerRef = useRef(null)
  const disposedRef = useRef(false)
  const [connected, setConnected] = useState(false)

  const connect = useCallback(() => {
    if (!host || !ttydPort || disposedRef.current) return
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${host}:${ttydPort}/ws`)
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      ws.send(JSON.stringify({ AuthToken: '', columns: 0, rows: 0 }))
      setConnected(true)
      retryRef.current = 0
    }

    ws.onclose = () => {
      setConnected(false)
      wsRef.current = null
      if (disposedRef.current) return
      const delay = RECONNECT_DELAYS[Math.min(retryRef.current, RECONNECT_DELAYS.length - 1)]
      retryRef.current++
      retryTimerRef.current = setTimeout(connect, delay)
    }

    ws.onerror = () => ws.close()

    wsRef.current = ws
  }, [host, ttydPort])

  useEffect(() => {
    disposedRef.current = false
    connect()
    return () => {
      disposedRef.current = true
      clearTimeout(retryTimerRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  const sendInput = useCallback((value) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    const payload = encoder.encode(value)
    const msg = new Uint8Array(1 + payload.length)
    msg[0] = TTYD_INPUT_CMD
    msg.set(payload, 1)
    ws.send(msg)
  }, [])

  const handleTouchStart = useCallback((value) => {
    sendInput(value)
    let timer = null
    const repeatTimer = setTimeout(() => {
      timer = setInterval(() => sendInput(value), KEY_REPEAT_INTERVAL)
    }, KEY_REPEAT_DELAY)

    const stop = () => {
      clearTimeout(repeatTimer)
      if (timer) clearInterval(timer)
      window.removeEventListener('touchend', stop)
      window.removeEventListener('touchcancel', stop)
    }
    window.addEventListener('touchend', stop)
    window.addEventListener('touchcancel', stop)
  }, [sendInput])

  if (!ttydPort) return null

  return (
    <div className="touch-only items-center justify-center gap-1.5 border-t border-gray-800 bg-gray-900 px-2 py-1.5 shrink-0">
      {KEYS.map((key) => {
        const Icon = key.icon
        return (
          <button
            key={key.label || key.title}
            title={key.title || key.label}
            disabled={!connected}
            onTouchStart={(e) => {
              e.preventDefault()
              handleTouchStart(key.value)
            }}
            onClick={() => sendInput(key.value)}
            className="flex h-9 min-w-[2.25rem] items-center justify-center rounded bg-gray-800 px-2 text-xs font-mono text-gray-300 active:bg-gray-600 disabled:opacity-30 transition-colors select-none"
          >
            {Icon ? <Icon className="h-4 w-4" /> : key.label}
          </button>
        )
      })}
    </div>
  )
}
```

Key differences from naive approach:
- `touch-only` CSS class (defined in Step 1) handles mobile detection — no Tailwind plugin needed
- `disposedRef` prevents zombie reconnections when props change or component unmounts
- `TextEncoder` hoisted to module scope (avoids allocation per keypress during repeat)

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/index.css dashboard/src/components/VirtualKeyboard.jsx
git commit -m "feat: add VirtualKeyboard component with ttyd WebSocket input"
```

---

### Task 2: Integrate into TerminalView

**Files:**
- Modify: `dashboard/src/components/TerminalView.jsx`

- [ ] **Step 1: Import VirtualKeyboard and render below iframe**

At the top of `TerminalView.jsx`, add the import:
```jsx
import VirtualKeyboard from './VirtualKeyboard'
```

Then modify the terminal section. Currently lines 77-83 are the iframe:
```jsx
        <iframe
          src={src}
          className="flex-1 w-full border-0"
          title={`Terminal: ${name}`}
          sandbox="allow-scripts allow-same-origin"
        />
```

Wrap it in a fragment and add VirtualKeyboard as a sibling:
```jsx
        <>
          <iframe
            src={src}
            className="flex-1 w-full border-0"
            title={`Terminal: ${name}`}
            sandbox="allow-scripts allow-same-origin"
          />
          <VirtualKeyboard host={host} ttydPort={ttydPort} />
        </>
```

The fragment is needed because the surrounding ternary expects a single expression. The iframe and VirtualKeyboard become direct children of the outer `flex flex-col` div, so `flex-1` on the iframe still works correctly. On desktop, VirtualKeyboard renders with `display: none` via the `touch-only` class and takes no space.

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/components/TerminalView.jsx
git commit -m "feat: integrate VirtualKeyboard into TerminalView"
```

---

### Task 3: Build and verify

- [ ] **Step 1: Build the dashboard**

```bash
cd /home/anders/repos/forsa-dev/dashboard && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 2: Verify production assets were generated**

Check that the built files in `src/forsa_dev/dashboard/static/assets/` have been updated.

- [ ] **Step 3: Manual test on phone**

Open the dashboard on the phone (portrait mode). Open a terminal session. Verify:
1. Virtual keyboard bar appears at the bottom
2. Arrow keys send correct input (test with Claude Code permission prompt)
3. Esc dismisses prompts
4. Ctrl+C interrupts
5. PageUp/PageDown scroll in tmux
6. Long-press on arrow key triggers repeat
7. Bar is not visible on desktop
8. Buttons show as disabled when ttyd is not running
9. Keyboard reconnects after ttyd restarts

- [ ] **Step 4: Commit build artifacts**

```bash
git add src/forsa_dev/dashboard/static/
git commit -m "build: update dashboard production assets"
```

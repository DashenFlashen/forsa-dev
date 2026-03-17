# Mobile Virtual Keyboard for Dashboard Terminal

## Problem

Using the dashboard's ttyd terminal from a phone (portrait mode) is impractical:
1. No arrow keys — Claude Code's interactive prompts require arrow up/down to navigate
2. No special keys — Esc, Tab, Ctrl+C are unavailable on mobile soft keyboards
3. No scrolling — can't scroll back through terminal output

## Solution

Add a virtual keyboard bar to the terminal view that appears only on touch devices. The bar renders below the ttyd iframe and communicates via a dedicated WebSocket connection to the ttyd server.

## Architecture

### Component: `VirtualKeyboard.jsx`

A React component rendered inside `TerminalView.jsx`, between the iframe and the bottom of the screen.

**Keys provided:**

| Key | Escape sequence / value |
|-----|------------------------|
| Up | `\x1b[A` |
| Down | `\x1b[B` |
| Left | `\x1b[D` |
| Right | `\x1b[C` |
| Esc | `\x1b` |
| Tab | `\t` |
| Ctrl+C | `\x03` |
| PgUp | `\x1b[5~` |
| PgDn | `\x1b[6~` |

**Layout:** Single row, compact buttons, styled to match the dark terminal theme. Arrow keys grouped together, modifiers on the other side.

### WebSocket Communication

The component opens its own WebSocket to the ttyd port using ttyd's binary protocol. The protocol is derived from `window.location.protocol` (`ws://` for HTTP, `wss://` for HTTPS).

**ttyd protocol constants (v1.7.4):**

| Byte | Command |
|------|---------|
| `0x00` | INPUT — send user input to the terminal |
| `0x01` | OUTPUT — terminal output (ignored by us) |
| `0x02` | SET_WINDOW_TITLE |
| `0x04` | SET_PREFERENCES |

**Connection sequence:**

1. **Connect** — open WebSocket to `ws://{host}:{ttydPort}/ws`
2. **Handshake** — send a JSON text frame: `{"AuthToken":"","columns":0,"rows":0}`. Auth token is empty since ttyd is started without `--credential`.
3. **Send input** — for each virtual key press, send a binary frame: `[0x00][utf8_payload]`
4. **Ignore output** — discard all incoming messages (the iframe handles display)

ttyd supports multiple simultaneous clients (default: unlimited), so this second connection coexists with the iframe's connection without conflict.

**Lifecycle:** WebSocket opens when the component mounts (terminal view opens on mobile), closes on unmount. On disconnect, the component attempts to reconnect with exponential backoff (1s, 2s, 4s, max 10s). Buttons are visually disabled while disconnected.

**Constraint:** ttyd must NOT be started with `--check-origin` (`-O`), as the dashboard page is served from a different port than ttyd.

### Mobile Detection

CSS media query `(pointer: coarse)` controls visibility:
- Touch devices: virtual keyboard is rendered, iframe gets `flex-1` minus keyboard height
- Mouse/trackpad devices: virtual keyboard is not rendered, iframe gets full height

No JavaScript feature detection needed.

### Integration with TerminalView

```
<div className="flex h-full w-full flex-col bg-gray-950">
  {/* header bar (existing) */}
  {/* iframe (existing, gets flex-1) */}
  {/* VirtualKeyboard — only rendered when ttydPort is set */}
</div>
```

The VirtualKeyboard receives `host` and `ttydPort` as props. It handles its own WebSocket lifecycle.

## Touch Scrolling

PageUp/PageDown buttons handle scrolling. In tmux, PageUp automatically enters copy mode and scrolls the buffer. PageDown scrolls forward. This is sufficient for reviewing conversation history.

## Files Changed

| File | Change |
|------|--------|
| `dashboard/src/components/VirtualKeyboard.jsx` | New component |
| `dashboard/src/components/TerminalView.jsx` | Import and render VirtualKeyboard below iframe |

## Files NOT Changed

- `src/forsa_dev/ttyd.py` — no ttyd configuration changes needed
- No custom ttyd index page
- No backend changes

## Native Soft Keyboard Coexistence

Tapping the iframe may trigger the native soft keyboard (ttyd's xterm.js uses a hidden textarea for input capture). The virtual key bar and native keyboard can coexist — the user uses the native keyboard for typing text and the virtual bar for special keys. The native keyboard can be dismissed by tapping outside the iframe or pressing the phone's back gesture.

## Key Repeat

Long-pressing an arrow key triggers repeated sends (via `setInterval` while touch is held, ~100ms interval). This is important for scrolling through output and navigating prompts.

## Risks

- **ttyd WebSocket protocol stability** — the binary protocol is undocumented. If ttyd changes it, the virtual keyboard breaks. Mitigated by: ttyd 1.7.4 is the installed version and unlikely to change without us noticing.
- **Dual WebSocket connections** — could theoretically cause issues with ttyd's client tracking. Mitigated by: ttyd is designed for multiple clients.
- **Viewport pressure** — in portrait mode with the native soft keyboard open, the terminal iframe will be small. Acceptable trade-off since the native keyboard is dismissible and the virtual bar is a single compact row.

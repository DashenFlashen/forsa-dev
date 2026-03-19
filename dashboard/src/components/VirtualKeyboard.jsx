import { useCallback } from 'react'
import {
  ArrowUp, ArrowDown, ArrowLeft, ArrowRight,
  ChevronsUp, ChevronsDown
} from 'lucide-react'

const KEYS = [
  { label: 'Esc', tmuxKey: 'Escape' },
  { label: 'Tab', tmuxKey: 'Tab' },
  { icon: ArrowUp, tmuxKey: 'Up' },
  { icon: ArrowDown, tmuxKey: 'Down' },
  { icon: ArrowLeft, tmuxKey: 'Left' },
  { icon: ArrowRight, tmuxKey: 'Right' },
  { label: 'C-c', tmuxKey: 'C-c' },
  { icon: ChevronsUp, tmuxKey: 'PPage', title: 'Page Up' },
  { icon: ChevronsDown, tmuxKey: 'NPage', title: 'Page Down' },
]

const KEY_REPEAT_INTERVAL = 100
const KEY_REPEAT_DELAY = 400

export default function VirtualKeyboard({ session }) {
  const sendKey = useCallback((tmuxKey) => {
    if (!session) return
    fetch(`/api/tmux/${encodeURIComponent(session)}/keys`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: tmuxKey }),
    }).catch(() => {})
  }, [session])

  const handleTouchStart = useCallback((tmuxKey) => {
    sendKey(tmuxKey)
    let timer = null
    const repeatTimer = setTimeout(() => {
      timer = setInterval(() => sendKey(tmuxKey), KEY_REPEAT_INTERVAL)
    }, KEY_REPEAT_DELAY)

    const stop = () => {
      clearTimeout(repeatTimer)
      if (timer) clearInterval(timer)
      window.removeEventListener('touchend', stop)
      window.removeEventListener('touchcancel', stop)
    }
    window.addEventListener('touchend', stop)
    window.addEventListener('touchcancel', stop)
  }, [sendKey])

  if (!session) return null

  return (
    <div className="touch-only items-center justify-center gap-1.5 border-t border-gray-800 bg-gray-900 px-2 py-1.5 shrink-0">
      {KEYS.map((key) => {
        const Icon = key.icon
        return (
          <button
            key={key.label || key.title}
            title={key.title || key.label}
            onTouchStart={(e) => {
              e.preventDefault()
              handleTouchStart(key.tmuxKey)
            }}
            onClick={() => sendKey(key.tmuxKey)}
            className="flex h-9 min-w-[2.25rem] items-center justify-center rounded bg-gray-800 px-2 text-xs font-mono text-gray-300 active:bg-gray-600 transition-colors select-none"
          >
            {Icon ? <Icon className="h-4 w-4" /> : key.label}
          </button>
        )
      })}
    </div>
  )
}

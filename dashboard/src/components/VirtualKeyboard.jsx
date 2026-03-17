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

import { useEffect, useRef, useState } from 'react'

const MAX_LINES = 1000

export default function LogsView({ envName }) {
  const [lines, setLines] = useState([])
  const [connected, setConnected] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    setLines([])
    const es = new EventSource(`/api/environments/${envName}/logs`)
    es.onopen = () => setConnected(true)
    es.onmessage = (e) => {
      setLines((prev) => {
        const next = [...prev, e.data]
        return next.length > MAX_LINES ? next.slice(-MAX_LINES) : next
      })
    }
    es.onerror = () => setConnected(false)
    return () => es.close()
  }, [envName])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'instant' })
  }, [lines])

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {!connected && lines.length === 0 && (
        <div className="px-4 py-2 text-xs text-gray-500 border-b border-gray-800 bg-gray-900">
          Connecting to log stream…
        </div>
      )}
      <div className="flex-1 overflow-y-auto bg-gray-950 p-4 font-mono text-xs">
        {lines.map((line, i) => (
          <div key={i} className="text-gray-300 whitespace-pre-wrap leading-5">{line || ' '}</div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

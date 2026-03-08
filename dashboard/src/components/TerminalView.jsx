import { useState } from 'react'
import { X, Terminal, ExternalLink } from 'lucide-react'
import StatusBadge from './StatusBadge'
import LogsView from './LogsView'

export default function TerminalView({ env, host, onClose }) {
  const [tab, setTab] = useState('terminal')
  const src = env.ttyd_port ? `http://${host}:${env.ttyd_port}` : null

  return (
    <div className="flex h-full w-full flex-col bg-gray-950">
      <div className="flex items-center gap-3 border-b border-gray-800 bg-gray-900 px-4 py-2.5 shrink-0">
        <Terminal className="h-4 w-4 shrink-0 text-gray-500" />
        <span className="font-mono text-sm font-medium text-gray-100">{env.name}</span>
        <StatusBadge status={env.status.server} />
        <div className="flex gap-1 ml-2">
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
          className="rounded p-1 text-gray-500 hover:bg-gray-800 hover:text-gray-200 transition-colors"
          aria-label="Close terminal"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {tab === 'logs' ? (
        <LogsView envName={env.name} />
      ) : src ? (
        <iframe
          src={src}
          className="flex-1 w-full border-0"
          title={`Terminal: ${env.name}`}
          sandbox="allow-scripts allow-same-origin"
        />
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-gray-500">
          <Terminal className="h-8 w-8 text-gray-700" />
          <p className="text-sm">Terminal not available</p>
        </div>
      )}
    </div>
  )
}

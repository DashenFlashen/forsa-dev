import { Code2, Terminal } from 'lucide-react'
import ActionButtons from './ActionButtons'
import StatusBadge from './StatusBadge'

export default function WorkspaceCard({ env, onAction, loading, onSelect }) {
  if (!env) return null

  const ttydAlive = env.status.ttyd === 'alive'

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-200">Workspace</h3>
          <p className="text-xs text-gray-500 font-mono mt-0.5">{env.branch}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={env.status.server} />
          <StatusBadge status={env.status.tmux} />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <ActionButtons
          env={env}
          onAction={onAction}
          loading={loading}
        />
        <button
          onClick={() => onSelect(env)}
          disabled={!ttydAlive}
          title={ttydAlive ? 'Open terminal' : 'Terminal not available'}
          aria-label="Open workspace terminal"
          className={`rounded-md p-2.5 transition-colors ${
            ttydAlive
              ? 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              : 'text-gray-600 cursor-not-allowed opacity-30'
          }`}
        >
          <Terminal className="h-4 w-4" />
        </button>
        <a
          href={`vscode://vscode-remote/ssh-remote+${window.location.hostname}${env.worktree}`}
          title="Open in VSCode"
          aria-label="Open workspace in VSCode"
          className="rounded-md p-2.5 text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-200"
        >
          <Code2 className="h-4 w-4" />
        </a>
        <a
          href={env.url}
          target="_blank"
          rel="noreferrer"
          className="font-mono text-sm text-blue-400 hover:text-blue-300 ml-auto"
        >
          :{env.port}
        </a>
        {env.uptime && (
          <span className="text-xs text-gray-500">{env.uptime}</span>
        )}
      </div>
    </div>
  )
}

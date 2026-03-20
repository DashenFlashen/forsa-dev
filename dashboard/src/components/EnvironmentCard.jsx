import { Code2, Terminal, Trash2 } from 'lucide-react'
import ActionButtons from './ActionButtons'
import ConfirmModal from './ConfirmModal'
import StatusBadge from './StatusBadge'
import UserInitials from './UserInitials'
import useDeleteConfirmation from '../hooks/useDeleteConfirmation'

export default function EnvironmentCard({ env, onAction, loadingAction, onSelect, isSelected, onDelete, loadingDelete }) {
  const { confirmDelete, handleDeleteClick, handleConfirmDelete, cancelDelete } = useDeleteConfirmation(onDelete, env)

  const branchDiffers = env.branch !== env.name
  const ttydAlive = env.status.ttyd === 'alive'
  const ageMs = Date.now() - new Date(env.created_at).getTime()
  const terminalReady = ttydAlive && ageMs >= 10_000

  return (
    <>
      <div
        onClick={() => onSelect(env)}
        className={`rounded-lg border p-4 theme-transition theme-card-hover ${
          isSelected
            ? 'border-blue-500 bg-gray-900'
            : 'border-gray-700/60 theme-card-bg active:bg-gray-900'
        }`}
      >
        {/* Row 1: name + user */}
        <div className="flex items-center justify-between">
          <span className="font-mono text-sm font-medium text-gray-100">{env.name}</span>
          <UserInitials user={env.user} className="h-7 w-7" />
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
            className="font-mono text-sm text-blue-400 active:text-blue-300"
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
            aria-label={`Open terminal for ${env.name}`}
            className={`rounded-md p-2.5 transition-colors ${
              terminalReady
                ? 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                : 'text-gray-600 cursor-not-allowed opacity-30'
            }`}
          >
            <Terminal className="h-4 w-4" />
          </button>
          <a
            href={`vscode://vscode-remote/ssh-remote+${window.location.hostname}${env.worktree}`}
            title="Open in VSCode"
            aria-label={`Open ${env.name} in VSCode`}
            className="rounded-md p-2.5 text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-200"
            onClick={(e) => e.stopPropagation()}
          >
            <Code2 className="h-4 w-4" />
          </a>
          {env.type !== 'repo' && (
            <button
              onClick={handleDeleteClick}
              disabled={loadingDelete}
              title="Delete environment"
              aria-label={`Delete ${env.name}`}
              className="rounded-md p-2.5 text-gray-500 transition-colors hover:bg-red-900/40 hover:text-red-400 disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {confirmDelete === 'normal' && (
        <ConfirmModal
          title={`Delete "${env.name}"?`}
          message="This will stop the server, remove the tmux session, and delete the git worktree."
          confirmLabel="Delete"
          danger
          onConfirm={handleConfirmDelete}
          onCancel={cancelDelete}
        />
      )}
      {confirmDelete === 'force' && (
        <ConfirmModal
          title="Branch not pushed — force delete?"
          message={`Branch '${env.branch}' has unpushed commits. Force delete will permanently discard them.`}
          confirmLabel="Force delete"
          danger
          onConfirm={handleConfirmDelete}
          onCancel={cancelDelete}
        />
      )}
    </>
  )
}

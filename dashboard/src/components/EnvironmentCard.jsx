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

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
      className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-gray-700 text-xs font-medium text-gray-300"
    >
      {initials}
    </span>
  )
}

export default function EnvironmentRow({ env, onAction, loadingAction, onSelect, isSelected, onDelete, loadingDelete }) {
  const [confirmDelete, setConfirmDelete] = useState(null) // null | 'normal' | 'force'

  const handleDeleteClick = (e) => {
    e.stopPropagation()
    setConfirmDelete('normal')
  }

  const handleConfirmDelete = async () => {
    const force = confirmDelete === 'force'
    setConfirmDelete(null)
    try {
      await onDelete(env.name, force)
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
      <tr
        className={`border-t border-gray-800 cursor-pointer transition-colors hover:bg-gray-900/60 ${
          isSelected
            ? 'bg-gray-900 border-l-2 border-l-blue-500'
            : 'border-l-2 border-l-transparent'
        }`}
        onClick={() => onSelect(env)}
      >
        <td className="px-4 py-3">
          <div className="flex flex-col">
            <span className="font-mono text-sm text-gray-100">{env.name}</span>
            {branchDiffers && (
              <span className="font-mono text-xs text-gray-500">{env.branch}</span>
            )}
          </div>
        </td>
        <td className="px-4 py-3">
          <UserInitials user={env.user} />
        </td>
        <td className="px-4 py-3">
          <StatusBadge status={env.status.server} />
        </td>
        <td className="px-4 py-3">
          <StatusBadge status={env.status.tmux} />
        </td>
        <td className="px-4 py-3 text-sm">
          <a
            href={env.url}
            target="_blank"
            rel="noreferrer"
            className="font-mono text-blue-400 hover:text-blue-300 hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            :{env.port}
          </a>
        </td>
        <td className="px-4 py-3 text-sm text-gray-400 tabular-nums">{env.uptime}</td>
        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center gap-1">
            <ActionButtons env={env} onAction={onAction} loading={loadingAction} />
            <button
              onClick={() => onSelect(env)}
              disabled={!terminalReady}
              title={!ttydAlive ? 'Terminal not available' : !terminalReady ? 'Terminal starting…' : 'Open terminal'}
              aria-label={`Open terminal for ${env.name}`}
              className={`rounded-md p-1.5 transition-colors ${
                terminalReady
                  ? 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                  : 'text-gray-600 cursor-not-allowed opacity-30'
              }`}
            >
              <Terminal className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={handleDeleteClick}
              disabled={loadingDelete}
              title="Delete environment"
              aria-label={`Delete ${env.name}`}
              className="rounded-md p-1.5 text-gray-500 transition-colors hover:bg-red-900/40 hover:text-red-400 disabled:opacity-50 ml-1"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </td>
      </tr>

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

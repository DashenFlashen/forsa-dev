import { Code2, Terminal, Trash2 } from 'lucide-react'
import ActionButtons from './ActionButtons'
import ConfirmModal from './ConfirmModal'
import StatusBadge from './StatusBadge'
import UserInitials from './UserInitials'
import useDeleteConfirmation from '../hooks/useDeleteConfirmation'

export default function EnvironmentRow({ env, onAction, loadingAction, onSelect, isSelected, onDelete, loadingDelete }) {
  const { confirmDelete, handleDeleteClick, handleConfirmDelete, cancelDelete } = useDeleteConfirmation(onDelete, env)

  const branchDiffers = env.branch !== env.name
  const ttydAlive = env.status.ttyd === 'alive'
  const ageMs = Date.now() - new Date(env.created_at).getTime()
  const terminalReady = ttydAlive && ageMs >= 10_000

  return (
    <>
      <tr
        className={`border-t border-gray-800 cursor-pointer theme-transition hover:bg-gray-900/60 ${
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
          <div className="flex items-center gap-1.5">
            <ActionButtons env={env} onAction={onAction} loading={loadingAction} />
            <button
              onClick={() => onSelect(env)}
              disabled={!terminalReady}
              title={!ttydAlive ? 'Terminal not available' : !terminalReady ? 'Terminal starting…' : 'Open terminal'}
              aria-label={`Open terminal for ${env.name}`}
              className={`rounded-md p-2 transition-colors ${
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
              className="rounded-md p-2 text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-200"
              onClick={(e) => e.stopPropagation()}
            >
              <Code2 className="h-4 w-4" />
            </a>
            <button
              onClick={handleDeleteClick}
              disabled={loadingDelete}
              title="Delete environment"
              aria-label={`Delete ${env.name}`}
              className="rounded-md p-2 text-gray-500 transition-colors hover:bg-red-900/40 hover:text-red-400 disabled:opacity-50 ml-1"
            >
              <Trash2 className="h-4 w-4" />
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

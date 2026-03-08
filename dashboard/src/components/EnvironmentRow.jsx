import ActionButtons from './ActionButtons'

const SERVER_COLORS = {
  running: 'text-green-400',
  crashed: 'text-red-400',
  stopped: 'text-gray-400',
}

const TMUX_COLORS = {
  active: 'text-green-400',
  detached: 'text-yellow-400',
  missing: 'text-red-400',
}

const TTYD_COLORS = {
  alive: 'text-green-400',
  dead: 'text-gray-400',
}

export default function EnvironmentRow({ env, onAction, loadingAction, onSelect, isSelected, onDelete, loadingDelete }) {
  return (
    <tr
      className={`border-t border-gray-800 cursor-pointer hover:bg-gray-900 ${isSelected ? 'bg-gray-900' : ''}`}
      onClick={() => onSelect(env)}
    >
      <td className="px-4 py-3 font-mono text-sm">{env.name}</td>
      <td className="px-4 py-3 text-sm text-gray-400">{env.user}</td>
      <td className="px-4 py-3 font-mono text-sm text-gray-400">{env.branch}</td>
      <td className={`px-4 py-3 text-sm ${SERVER_COLORS[env.status.server] ?? 'text-gray-400'}`}>
        {env.status.server}
      </td>
      <td className={`px-4 py-3 text-sm ${TMUX_COLORS[env.status.tmux] ?? 'text-gray-400'}`}>
        {env.status.tmux}
      </td>
      <td className={`px-4 py-3 text-sm ${TTYD_COLORS[env.status.ttyd] ?? 'text-gray-400'}`}>
        {env.status.ttyd ?? '-'}
      </td>
      <td className="px-4 py-3 text-sm">
        <a
          href={env.url}
          target="_blank"
          rel="noreferrer"
          className="text-blue-400 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          :{env.port}
        </a>
      </td>
      <td className="px-4 py-3 text-sm text-gray-400">{env.uptime}</td>
      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2">
          <ActionButtons env={env} onAction={onAction} loading={loadingAction} />
          <button
            onClick={() => onDelete(env.name)}
            disabled={loadingDelete}
            className="text-gray-500 hover:text-red-400 disabled:opacity-50"
            title="Delete environment"
            aria-label={`Delete ${env.name}`}
          >
            {loadingDelete ? '…' : '🗑'}
          </button>
        </div>
      </td>
    </tr>
  )
}

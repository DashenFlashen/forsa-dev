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

export default function EnvironmentRow({ env, onAction, loadingAction }) {
  return (
    <tr className="border-t border-gray-800 hover:bg-gray-900">
      <td className="px-4 py-3 font-mono text-sm">{env.name}</td>
      <td className="px-4 py-3 text-sm text-gray-400">{env.user}</td>
      <td className="px-4 py-3 font-mono text-sm text-gray-400">{env.branch}</td>
      <td className={`px-4 py-3 text-sm ${SERVER_COLORS[env.status.server] ?? 'text-gray-400'}`}>
        {env.status.server}
      </td>
      <td className={`px-4 py-3 text-sm ${TMUX_COLORS[env.status.tmux] ?? 'text-gray-400'}`}>
        {env.status.tmux}
      </td>
      <td className="px-4 py-3 text-sm">
        <a
          href={env.url}
          target="_blank"
          rel="noreferrer"
          className="text-blue-400 hover:underline"
        >
          :{env.port}
        </a>
      </td>
      <td className="px-4 py-3 text-sm text-gray-400">{env.uptime}</td>
      <td className="px-4 py-3">
        <ActionButtons env={env} onAction={onAction} loading={loadingAction} />
      </td>
    </tr>
  )
}

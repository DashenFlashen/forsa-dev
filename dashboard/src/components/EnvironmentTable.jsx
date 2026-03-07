import EnvironmentRow from './EnvironmentRow'

export default function EnvironmentTable({ envs, onAction, loadingActions }) {
  if (envs.length === 0) {
    return (
      <p className="text-center text-gray-500 py-8">
        No environments found. Run <code className="font-mono text-gray-300">forsa-dev up &lt;name&gt;</code> to create one.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-800">
      <table className="w-full text-left">
        <thead className="bg-gray-900 text-xs uppercase tracking-wide text-gray-400">
          <tr>
            <th className="px-4 py-3">Name</th>
            <th className="px-4 py-3">User</th>
            <th className="px-4 py-3">Branch</th>
            <th className="px-4 py-3">Server</th>
            <th className="px-4 py-3">Tmux</th>
            <th className="px-4 py-3">Port</th>
            <th className="px-4 py-3">Uptime</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {envs.map((env) => (
            <EnvironmentRow
              key={`${env.user}-${env.name}`}
              env={env}
              onAction={onAction}
              loadingAction={loadingActions[env.name]}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

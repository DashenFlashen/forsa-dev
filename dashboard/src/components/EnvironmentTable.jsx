import { Plus } from 'lucide-react'
import EnvironmentCard from './EnvironmentCard'
import EnvironmentRow from './EnvironmentRow'

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 rounded-full bg-gray-800 p-4">
        <Plus className="h-8 w-8 text-gray-500" />
      </div>
      <h3 className="mb-1 text-base font-semibold text-gray-300">No environments yet</h3>
      <p className="text-sm text-gray-500">
        Use the form above to create your first development environment.
      </p>
    </div>
  )
}

export default function EnvironmentTable({ envs, onAction, loadingActions, onSelect, selectedEnv, onDelete, loadingDeletes }) {
  if (envs.length === 0) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-900/50">
        <EmptyState />
      </div>
    )
  }

  return (
    <>
      {/* Mobile: card layout */}
      <div className="flex flex-col gap-3 lg:hidden">
        {envs.map((env) => (
          <EnvironmentCard
            key={`${env.user}-${env.name}`}
            env={env}
            onAction={onAction}
            loadingAction={loadingActions[`${env.user}/${env.name}`]}
            onSelect={onSelect}
            isSelected={selectedEnv?.user === env.user && selectedEnv?.name === env.name}
            onDelete={onDelete}
            loadingDelete={!!loadingDeletes[`${env.user}/${env.name}`]}
          />
        ))}
      </div>

      {/* Desktop: table layout */}
      <div className="hidden overflow-x-auto rounded-lg border border-gray-800 lg:block">
        <table className="w-full text-left">
          <thead className="bg-gray-900 text-xs uppercase tracking-wider text-gray-500">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">User</th>
              <th className="px-4 py-3 font-medium">Server</th>
              <th className="px-4 py-3 font-medium">Tmux</th>
              <th className="px-4 py-3 font-medium">Port</th>
              <th className="px-4 py-3 font-medium">Uptime</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {envs.map((env) => (
              <EnvironmentRow
                key={`${env.user}-${env.name}`}
                env={env}
                onAction={onAction}
                loadingAction={loadingActions[`${env.user}/${env.name}`]}
                onSelect={onSelect}
                isSelected={selectedEnv?.user === env.user && selectedEnv?.name === env.name}
                onDelete={onDelete}
                loadingDelete={!!loadingDeletes[`${env.user}/${env.name}`]}
              />
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

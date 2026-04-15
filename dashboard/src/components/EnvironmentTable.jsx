import { useState } from 'react'
import { Archive, ChevronDown, ChevronRight, Plus } from 'lucide-react'
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

function EnvCards({ envs, onAction, loadingActions, onSelect, selectedEnv, onDelete, loadingDeletes, onArchive }) {
  return envs.map((env) => (
    <EnvironmentCard
      key={`${env.user}-${env.name}`}
      env={env}
      onAction={onAction}
      loadingAction={loadingActions[`${env.user}/${env.name}`]}
      onSelect={onSelect}
      isSelected={selectedEnv?.user === env.user && selectedEnv?.name === env.name}
      onDelete={onDelete}
      loadingDelete={!!loadingDeletes[`${env.user}/${env.name}`]}
      onArchive={onArchive}
    />
  ))
}

function EnvRows({ envs, onAction, loadingActions, onSelect, selectedEnv, onDelete, loadingDeletes, onArchive }) {
  return envs.map((env) => (
    <EnvironmentRow
      key={`${env.user}-${env.name}`}
      env={env}
      onAction={onAction}
      loadingAction={loadingActions[`${env.user}/${env.name}`]}
      onSelect={onSelect}
      isSelected={selectedEnv?.user === env.user && selectedEnv?.name === env.name}
      onDelete={onDelete}
      loadingDelete={!!loadingDeletes[`${env.user}/${env.name}`]}
      onArchive={onArchive}
    />
  ))
}

const TABLE_HEADER = (
  <thead className="bg-gray-900 text-xs uppercase tracking-wider text-gray-500">
    <tr>
      <th className="px-4 py-3 font-medium">Name</th>
      <th className="px-4 py-3 font-medium">User</th>
      <th className="px-4 py-3 font-medium">Status</th>
      <th className="px-4 py-3 font-medium">Port</th>
      <th className="px-4 py-3 font-medium">Uptime</th>
      <th className="px-4 py-3 font-medium">Actions</th>
    </tr>
  </thead>
)

export default function EnvironmentTable({ envs, onAction, loadingActions, onSelect, selectedEnv, onDelete, loadingDeletes, onArchive }) {
  const [archivedOpen, setArchivedOpen] = useState(false)

  if (envs.length === 0) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-900/50">
        <EmptyState />
      </div>
    )
  }

  const activeEnvs = envs.filter((e) => !e.archived)
  const archivedEnvs = envs.filter((e) => e.archived)
  const shared = { onAction, loadingActions, onSelect, selectedEnv, onDelete, loadingDeletes, onArchive }

  return (
    <>
      {/* Mobile: card layout */}
      <div className="flex flex-col gap-3 lg:hidden">
        <EnvCards envs={activeEnvs} {...shared} />
        {archivedEnvs.length > 0 && (
          <>
            <button
              onClick={() => setArchivedOpen((v) => !v)}
              className="flex items-center gap-2 px-1 py-2 text-sm text-gray-500 hover:text-gray-300 transition-colors"
            >
              {archivedOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              <Archive className="h-3.5 w-3.5" />
              Archived ({archivedEnvs.length})
            </button>
            {archivedOpen && <EnvCards envs={archivedEnvs} {...shared} />}
          </>
        )}
      </div>

      {/* Desktop: table layout */}
      <div className="hidden lg:flex lg:flex-col lg:gap-4">
        <div className="overflow-x-auto rounded-lg border border-gray-800">
          <table className="w-full text-left">
            {TABLE_HEADER}
            <tbody>
              <EnvRows envs={activeEnvs} {...shared} />
            </tbody>
          </table>
        </div>
        {archivedEnvs.length > 0 && (
          <>
            <button
              onClick={() => setArchivedOpen((v) => !v)}
              className="flex items-center gap-2 px-1 py-1 text-sm text-gray-500 hover:text-gray-300 transition-colors"
            >
              {archivedOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              <Archive className="h-3.5 w-3.5" />
              Archived ({archivedEnvs.length})
            </button>
            {archivedOpen && (
              <div className="overflow-x-auto rounded-lg border border-gray-800">
                <table className="w-full text-left">
                  {TABLE_HEADER}
                  <tbody>
                    <EnvRows envs={archivedEnvs} {...shared} />
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </>
  )
}

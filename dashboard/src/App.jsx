import { useCallback, useEffect, useState } from 'react'
import AgentButtons from './components/AgentButtons'
import CreateEnvironment from './components/CreateEnvironment'
import EnvironmentTable from './components/EnvironmentTable'
import WorkspaceCard from './components/WorkspaceCard'
import ErrorToast from './components/ErrorToast'
import HealthPanel from './components/HealthPanel'
import TerminalView from './components/TerminalView'
import UserPicker from './components/UserPicker'
import UserInitials from './components/UserInitials'
import useInterval from './hooks/useInterval'

const ENV_POLL_MS = 3000
const HEALTH_POLL_MS = 10000

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'))
  return match ? match[2] : null
}

function setCookie(name, value) {
  document.cookie = `${name}=${value}; path=/; max-age=31536000`
}

function clearCookie(name) {
  document.cookie = `${name}=; path=/; max-age=0`
}

async function apiFetch(path, options) {
  const resp = await fetch(path, options)
  if (!resp.ok) {
    let detail = `${options?.method ?? 'GET'} ${path} failed: ${resp.status}`
    try {
      const body = await resp.json()
      if (body.detail) detail = body.detail
    } catch { /* no JSON body */ }
    const err = new Error(detail)
    err.status = resp.status
    throw err
  }
  return resp.json()
}

export default function App() {
  const [user, setUser] = useState(() => getCookie('forsa_user'))
  const [envs, setEnvs] = useState([])
  const [health, setHealth] = useState(null)
  const [defaultDataDir, setDefaultDataDir] = useState('')
  const [error, setError] = useState(null)
  const [loadingActions, setLoadingActions] = useState({})
  const [loadingDeletes, setLoadingDeletes] = useState({})
  const [selectedEnv, setSelectedEnv] = useState(null)
  const [selectedAgent, setSelectedAgent] = useState(null)

  const handleSelectUser = useCallback((name) => {
    setCookie('forsa_user', name)
    setUser(name)
  }, [])

  const handleSwitchUser = useCallback(() => {
    clearCookie('forsa_user')
    setUser(null)
  }, [])

  const fetchEnvs = useCallback(async () => {
    try {
      const data = await apiFetch('/api/environments')
      setEnvs(data)
      setError(null)
    } catch {
      setError('Cannot reach dashboard API. Is the server running?')
    }
  }, [])

  const fetchHealth = useCallback(async () => {
    try {
      const data = await apiFetch('/api/health')
      setHealth(data)
    } catch {
      // health failures are non-critical
    }
  }, [])

  // Initial fetch on mount
  useEffect(() => {
    if (!user) return
    fetchEnvs()
    fetchHealth()
    apiFetch('/api/config').then((d) => setDefaultDataDir(d.data_dir)).catch(() => {})
  }, [user, fetchEnvs, fetchHealth])

  useInterval(fetchEnvs, user ? ENV_POLL_MS : null)
  useInterval(fetchHealth, user ? HEALTH_POLL_MS : null)

  const handleAction = useCallback(async (owner, name, action) => {
    const key = `${owner}/${name}`
    setLoadingActions((prev) => ({ ...prev, [key]: action }))
    try {
      await apiFetch(`/api/environments/${owner}/${name}/${action}`, { method: 'POST' })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoadingActions((prev) => ({ ...prev, [key]: null }))
      fetchEnvs()
    }
  }, [fetchEnvs])

  const handleCreate = useCallback(async (name, fromBranch, dataDir, existingBranch = null) => {
    try {
      await apiFetch('/api/environments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          from_branch: fromBranch,
          data_dir: dataDir || null,
          existing_branch: existingBranch || null,
        }),
      })
      await fetchEnvs()
    } catch (e) {
      setError(e.message)
    }
  }, [fetchEnvs])

  const handleArchive = useCallback(async (owner, name) => {
    try {
      await apiFetch(`/api/environments/${owner}/${name}/archive`, { method: 'POST' })
      await fetchEnvs()
    } catch (e) {
      setError(e.message)
    }
  }, [fetchEnvs])

  const handleDelete = useCallback(async (owner, name, force = false) => {
    const key = `${owner}/${name}`
    setLoadingDeletes((prev) => ({ ...prev, [key]: true }))
    try {
      const url = force
        ? `/api/environments/${owner}/${name}?force=true`
        : `/api/environments/${owner}/${name}`
      await apiFetch(url, { method: 'DELETE' })
      if (selectedEnv?.name === name && selectedEnv?.user === owner) setSelectedEnv(null)
      await fetchEnvs()
    } catch (e) {
      if (e.status === 409) {
        throw e  // EnvironmentRow/Card handles the force-delete modal
      } else {
        setError(e.message)
      }
    } finally {
      setLoadingDeletes((prev) => ({ ...prev, [key]: false }))
    }
  }, [fetchEnvs, selectedEnv])

  const handleSelect = useCallback((env) => {
    setSelectedEnv((prev) => prev?.name === env.name && prev?.user === env.user ? null : env)
  }, [])

  const handleCloseTerminal = useCallback(() => setSelectedEnv(null), [])

  // Derive host from current page location
  const host = window.location.hostname

  const workspaceEnv = envs.find((e) => e.type === 'repo' && e.user === user)
  const worktreeEnvs = envs.filter((e) => e.type !== 'repo')

  if (!user) {
    return <UserPicker onSelect={handleSelectUser} />
  }

  return (
    <div className="min-h-screen bg-gray-950">
      <header className="border-b border-gray-800 theme-header">
        <div className="mx-auto max-w-7xl px-4 py-3 lg:px-6 lg:py-4 flex items-center gap-3">
          <span className="text-lg font-bold tracking-tight text-gray-100">forsa-dev</span>
          {health && (
            <span className="hidden text-xs text-gray-500 font-mono lg:inline">
              {host}
            </span>
          )}
          <AgentButtons onSelectAgent={setSelectedAgent} />
          <div className="ml-auto flex items-center gap-3 text-sm text-gray-400">
            <UserInitials user={user} className="h-8 w-8 text-sm" />
            <span className="font-medium text-gray-200 capitalize">{user}</span>
            <button
              onClick={handleSwitchUser}
              className="text-blue-400 hover:text-blue-300 hover:underline"
            >
              switch
            </button>
          </div>
        </div>
      </header>
      <ErrorToast message={error} onDismiss={() => setError(null)} />
      <main className="mx-auto max-w-7xl px-4 py-4 lg:px-6 lg:py-6 space-y-4">
        <HealthPanel health={health} />
        <WorkspaceCard
          env={workspaceEnv}
          onAction={handleAction}
          loading={workspaceEnv ? loadingActions[`${workspaceEnv.user}/${workspaceEnv.name}`] : null}
          onSelect={handleSelect}
        />
        <CreateEnvironment onCreate={handleCreate} defaultDataDir={defaultDataDir} />
        <EnvironmentTable
          envs={worktreeEnvs}
          onAction={handleAction}
          loadingActions={loadingActions}
          onSelect={handleSelect}
          selectedEnv={selectedEnv}
          onDelete={handleDelete}
          loadingDeletes={loadingDeletes}
          onArchive={handleArchive}
        />
        {/* Fullscreen terminal overlay — same for mobile and desktop */}
        {selectedEnv && (
          <div className="fixed inset-0 z-50 flex flex-col bg-gray-950">
            <TerminalView
              env={selectedEnv}
              host={host}
              onClose={handleCloseTerminal}
              onAction={handleAction}
              loadingAction={loadingActions[`${selectedEnv.user}/${selectedEnv.name}`]}
            />
          </div>
        )}
        {selectedAgent && (
          <div className="fixed inset-0 z-50 flex flex-col bg-gray-950">
            <TerminalView
              agent={selectedAgent}
              host={host}
              onClose={() => setSelectedAgent(null)}
            />
          </div>
        )}
      </main>
    </div>
  )
}

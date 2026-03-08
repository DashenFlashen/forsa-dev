import { useCallback, useEffect, useState } from 'react'
import CreateEnvironment from './components/CreateEnvironment'
import ImportBranch from './components/ImportBranch'
import EnvironmentTable from './components/EnvironmentTable'
import ErrorToast from './components/ErrorToast'
import HealthPanel from './components/HealthPanel'
import TerminalView from './components/TerminalView'
import useInterval from './hooks/useInterval'

const ENV_POLL_MS = 3000
const HEALTH_POLL_MS = 10000

async function apiFetch(path, options) {
  const resp = await fetch(path, options)
  if (!resp.ok) throw new Error(`${options?.method ?? 'GET'} ${path} failed: ${resp.status}`)
  return resp.json()
}

export default function App() {
  const [envs, setEnvs] = useState([])
  const [health, setHealth] = useState(null)
  const [defaultDataDir, setDefaultDataDir] = useState('')
  const [error, setError] = useState(null)
  const [loadingActions, setLoadingActions] = useState({})
  const [loadingDeletes, setLoadingDeletes] = useState({})
  const [selectedEnv, setSelectedEnv] = useState(null)

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
    fetchEnvs()
    fetchHealth()
    apiFetch('/api/config').then((d) => setDefaultDataDir(d.data_dir)).catch(() => {})
  }, [fetchEnvs, fetchHealth])

  useInterval(fetchEnvs, ENV_POLL_MS)
  useInterval(fetchHealth, HEALTH_POLL_MS)

  const handleAction = useCallback(async (name, action) => {
    setLoadingActions((prev) => ({ ...prev, [name]: action }))
    try {
      await apiFetch(`/api/environments/${name}/${action}`, { method: 'POST' })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoadingActions((prev) => ({ ...prev, [name]: null }))
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

  const handleDelete = useCallback(async (name, force = false) => {
    setLoadingDeletes((prev) => ({ ...prev, [name]: true }))
    try {
      const url = force ? `/api/environments/${name}?force=true` : `/api/environments/${name}`
      await apiFetch(url, { method: 'DELETE' })
      if (selectedEnv?.name === name) setSelectedEnv(null)
      await fetchEnvs()
    } catch (e) {
      if (e.message.includes('409')) {
        throw e  // EnvironmentRow handles the force-delete modal
      } else {
        setError(e.message)
      }
    } finally {
      setLoadingDeletes((prev) => ({ ...prev, [name]: false }))
    }
  }, [fetchEnvs, selectedEnv])

  const handleSelect = useCallback((env) => {
    setSelectedEnv((prev) => prev?.name === env.name ? null : env)
  }, [])

  const handleCloseTerminal = useCallback(() => setSelectedEnv(null), [])

  // Derive host from current page location
  const host = window.location.hostname

  return (
    <div className="min-h-screen bg-gray-950">
      <header className="border-b border-gray-800 bg-gray-900">
        <div className="mx-auto max-w-7xl px-6 py-4 flex items-center gap-3">
          <span className="text-lg font-bold tracking-tight text-gray-100">forsa-dev</span>
          {health && (
            <span className="text-xs text-gray-500 font-mono">
              {host}
            </span>
          )}
        </div>
      </header>
      <ErrorToast message={error} onDismiss={() => setError(null)} />
      <main className="mx-auto max-w-7xl px-6 py-6 space-y-6">
        <HealthPanel health={health} />
        <CreateEnvironment onCreate={handleCreate} defaultDataDir={defaultDataDir} />
        <ImportBranch onCreate={handleCreate} defaultDataDir={defaultDataDir} />
        <div className={`flex gap-4 transition-all duration-300 ${selectedEnv ? 'lg:flex-row' : ''}`}>
          <div className={`transition-all duration-300 ${selectedEnv ? 'lg:w-1/3' : 'w-full'}`}>
            <EnvironmentTable
              envs={envs}
              onAction={handleAction}
              loadingActions={loadingActions}
              onSelect={handleSelect}
              selectedEnv={selectedEnv}
              onDelete={handleDelete}
              loadingDeletes={loadingDeletes}
            />
          </div>
          {selectedEnv && (
            <div className="hidden lg:flex flex-1 h-[600px] rounded-lg border border-gray-800 overflow-hidden">
              <TerminalView env={selectedEnv} host={host} onClose={handleCloseTerminal} />
            </div>
          )}
        </div>
        {/* Mobile: full-screen terminal overlay */}
        {selectedEnv && (
          <div className="fixed inset-0 z-50 flex flex-col bg-gray-950 lg:hidden">
            <TerminalView env={selectedEnv} host={host} onClose={handleCloseTerminal} />
          </div>
        )}
      </main>
    </div>
  )
}

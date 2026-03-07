import { useCallback, useEffect, useState } from 'react'
import ErrorBanner from './components/ErrorBanner'
import EnvironmentTable from './components/EnvironmentTable'
import HealthBar from './components/HealthBar'

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
  const [error, setError] = useState(null)
  const [loadingActions, setLoadingActions] = useState({})

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

  useEffect(() => {
    fetchEnvs()
    fetchHealth()
    const envTimer = setInterval(fetchEnvs, ENV_POLL_MS)
    const healthTimer = setInterval(fetchHealth, HEALTH_POLL_MS)
    return () => {
      clearInterval(envTimer)
      clearInterval(healthTimer)
    }
  }, [fetchEnvs, fetchHealth])

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

  return (
    <div className="mx-auto max-w-6xl p-6">
      <h1 className="mb-6 text-2xl font-bold text-gray-100">forsa-dev</h1>
      <ErrorBanner message={error} />
      <HealthBar health={health} />
      <EnvironmentTable envs={envs} onAction={handleAction} loadingActions={loadingActions} />
    </div>
  )
}

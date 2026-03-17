import { useEffect, useState } from 'react'
import { Plus, Download, RefreshCw } from 'lucide-react'
import CollapsibleSection from './CollapsibleSection'

const NAME_RE = /^[a-z0-9][a-z0-9_-]*$/

function deriveName(branch) {
  return branch.split('/').pop().toLowerCase().replace(/[^a-z0-9_-]/g, '-').replace(/^-+/, '')
}

export default function CreateEnvironment({ onCreate, defaultDataDir }) {
  const [tab, setTab] = useState('new')
  const [name, setName] = useState('')
  const [dataDir, setDataDir] = useState('')
  const [loading, setLoading] = useState(false)
  const [showOptions, setShowOptions] = useState(false)

  // "From branch" state
  const [branches, setBranches] = useState([])
  const [branch, setBranch] = useState('')
  const [branchName, setBranchName] = useState('')
  const [loadingBranches, setLoadingBranches] = useState(true)

  useEffect(() => {
    fetch('/api/branches')
      .then((r) => r.json())
      .then((d) => { setBranches(d.branches); setLoadingBranches(false) })
      .catch(() => setLoadingBranches(false))
  }, [])

  useEffect(() => {
    if (defaultDataDir && !dataDir) setDataDir(defaultDataDir)
  }, [defaultDataDir])

  function handleBranchChange(e) {
    const b = e.target.value
    setBranch(b)
    setBranchName(b ? deriveName(b) : '')
  }

  async function handleNewSubmit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    try {
      await onCreate(name.trim(), 'main', dataDir.trim() || null)
      setName('')
    } finally {
      setLoading(false)
    }
  }

  async function handleBranchSubmit(e) {
    e.preventDefault()
    if (!branch || !branchName.trim()) return
    setLoading(true)
    try {
      await onCreate(branchName.trim(), 'main', dataDir.trim() || null, branch)
      setBranch('')
      setBranchName('')
    } finally {
      setLoading(false)
    }
  }

  const branchNameValid = NAME_RE.test(branchName)

  return (
    <CollapsibleSection title="Create Environment">
      {/* Tabs */}
      <div className="mb-3 flex gap-1">
        {['new', 'branch'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
              tab === t
                ? 'bg-gray-700 text-gray-100'
                : 'text-gray-500 hover:bg-gray-800 hover:text-gray-300'
            }`}
          >
            {t === 'new' ? 'New' : 'From branch'}
          </button>
        ))}
      </div>

      {/* New tab */}
      {tab === 'new' && (
        <form onSubmit={handleNewSubmit} className="flex flex-col gap-2">
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Name (e.g. ticket-42)"
              className="flex-1 min-w-48 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
            />
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {loading ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="h-3.5 w-3.5" />
              )}
              {loading ? 'Creating…' : 'Create'}
            </button>
          </div>
          {showOptions ? (
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500 whitespace-nowrap w-16">Data dir</label>
              <input
                type="text"
                value={dataDir}
                onChange={(e) => setDataDir(e.target.value)}
                placeholder="/data/dev"
                className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm font-mono text-gray-300 placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowOptions(true)}
              className="self-start text-xs text-gray-500 hover:text-gray-400"
            >
              Options…
            </button>
          )}
        </form>
      )}

      {/* From branch tab */}
      {tab === 'branch' && (
        <form onSubmit={handleBranchSubmit} className="flex flex-col gap-2">
          <div className="flex flex-wrap gap-2">
            <select
              value={branch}
              onChange={handleBranchChange}
              disabled={loadingBranches}
              className="flex-1 min-w-48 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 disabled:opacity-50"
            >
              <option value="">{loadingBranches ? 'Loading…' : 'Select branch…'}</option>
              {branches.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
            <input
              type="text"
              value={branchName}
              onChange={(e) => setBranchName(e.target.value)}
              placeholder="Environment name"
              className={`flex-1 min-w-32 rounded-md border px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 ${
                branchName && !branchNameValid
                  ? 'border-red-500 bg-gray-800 focus:ring-red-500/50'
                  : 'border-gray-700 bg-gray-800 focus:border-blue-500 focus:ring-blue-500/50'
              }`}
            />
            <button
              type="submit"
              disabled={loading || !branch || !branchNameValid}
              className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {loading
                ? <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                : <Download className="h-3.5 w-3.5" />}
              {loading ? 'Importing…' : 'Import'}
            </button>
          </div>
          {showOptions ? (
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500 whitespace-nowrap w-16">Data dir</label>
              <input
                type="text"
                value={dataDir}
                onChange={(e) => setDataDir(e.target.value)}
                placeholder="/data/dev"
                className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm font-mono text-gray-300 placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowOptions(true)}
              className="self-start text-xs text-gray-500 hover:text-gray-400"
            >
              Options…
            </button>
          )}
        </form>
      )}
    </CollapsibleSection>
  )
}

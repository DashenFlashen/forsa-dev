import { useEffect, useState } from 'react'
import { Download, RefreshCw } from 'lucide-react'

const NAME_RE = /^[a-z0-9][a-z0-9_-]*$/

function deriveName(branch) {
  return branch.split('/').pop().toLowerCase().replace(/[^a-z0-9_-]/g, '-').replace(/^-+/, '')
}

export default function ImportBranch({ onCreate, defaultDataDir }) {
  const [branches, setBranches] = useState([])
  const [branch, setBranch] = useState('')
  const [name, setName] = useState('')
  const [dataDir, setDataDir] = useState('')
  const [loading, setLoading] = useState(false)
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
    setName(b ? deriveName(b) : '')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!branch || !name.trim()) return
    setLoading(true)
    try {
      await onCreate(name.trim(), 'main', dataDir.trim() || null, branch)
      setBranch('')
      setName('')
    } finally {
      setLoading(false)
    }
  }

  const nameValid = NAME_RE.test(name)

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 px-5 py-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
        Import Branch
      </h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
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
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Environment name"
            className={`flex-1 min-w-32 rounded-md border px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 ${
              name && !nameValid
                ? 'border-red-500 bg-gray-800 focus:ring-red-500/50'
                : 'border-gray-700 bg-gray-800 focus:border-blue-500 focus:ring-blue-500/50'
            }`}
          />
          <button
            type="submit"
            disabled={loading || !branch || !nameValid}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
          >
            {loading
              ? <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              : <Download className="h-3.5 w-3.5" />}
            {loading ? 'Importing…' : 'Import'}
          </button>
        </div>
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
      </form>
    </div>
  )
}

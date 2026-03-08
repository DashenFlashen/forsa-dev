import { useState } from 'react'
import { Plus, RefreshCw } from 'lucide-react'

const BRANCH_OPTIONS = ['main', 'develop']

export default function CreateEnvironment({ onCreate }) {
  const [name, setName] = useState('')
  const [branch, setBranch] = useState('main')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    try {
      await onCreate(name.trim(), branch)
      setName('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 px-5 py-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
        New Environment
      </h2>
      <form onSubmit={handleSubmit} className="flex flex-wrap gap-2">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name (e.g. ticket-42)"
          className="flex-1 min-w-48 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
        />
        <select
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-300 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
        >
          {BRANCH_OPTIONS.map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
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
      </form>
    </div>
  )
}

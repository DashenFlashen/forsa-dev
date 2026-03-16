import { useEffect, useState } from 'react'
import { Plus, RefreshCw } from 'lucide-react'
import CollapsibleSection from './CollapsibleSection'

export default function CreateEnvironment({ onCreate, defaultDataDir }) {
  const [name, setName] = useState('')
  const [dataDir, setDataDir] = useState('')
  const [loading, setLoading] = useState(false)
  const [showOptions, setShowOptions] = useState(false)

  useEffect(() => {
    if (defaultDataDir && !dataDir) setDataDir(defaultDataDir)
  }, [defaultDataDir])

  async function handleSubmit(e) {
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

  return (
    <CollapsibleSection title="New Environment">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
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
    </CollapsibleSection>
  )
}

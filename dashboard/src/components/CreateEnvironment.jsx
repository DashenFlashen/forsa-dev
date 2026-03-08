import { useState } from 'react'

export default function CreateEnvironment({ onCreate }) {
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    try {
      await onCreate(name.trim())
      setName('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 flex gap-2">
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Environment name (e.g. ticket-42)"
        className="flex-1 rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
      />
      <button
        type="submit"
        disabled={loading || !name.trim()}
        className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Creating…' : 'Create'}
      </button>
    </form>
  )
}

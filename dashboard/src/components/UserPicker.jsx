import { useEffect, useState } from 'react'

export default function UserPicker({ onSelect }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/users')
      .then((r) => r.json())
      .then((data) => {
        setUsers(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950">
      <div className="text-center">
        <h1 className="mb-2 text-2xl font-bold text-gray-100">forsa-dev</h1>
        <p className="mb-8 text-gray-400">Who are you?</p>
        <div className="flex flex-col gap-3">
          {users.map((u) => (
            <button
              key={u.name}
              onClick={() => onSelect(u.name)}
              className="rounded-lg bg-gray-800 px-8 py-3 text-lg font-medium text-gray-100 theme-transition theme-card-hover capitalize"
            >
              {u.name}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

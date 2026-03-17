import { useState } from 'react'

export default function useDeleteConfirmation(onDelete, env) {
  const [confirmDelete, setConfirmDelete] = useState(null) // null | 'normal' | 'force'

  const handleDeleteClick = (e) => {
    e.stopPropagation()
    setConfirmDelete('normal')
  }

  const handleConfirmDelete = async () => {
    const force = confirmDelete === 'force'
    setConfirmDelete(null)
    try {
      await onDelete(env.user, env.name, force)
    } catch (e) {
      if (e.status === 409) {
        setConfirmDelete('force')
      }
    }
  }

  const cancelDelete = () => setConfirmDelete(null)

  return { confirmDelete, handleDeleteClick, handleConfirmDelete, cancelDelete }
}

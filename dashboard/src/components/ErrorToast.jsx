import { useEffect } from 'react'
import { AlertCircle, X } from 'lucide-react'

export default function ErrorToast({ message, onDismiss }) {
  useEffect(() => {
    if (!message) return
    const id = setTimeout(onDismiss, 6000)
    return () => clearTimeout(id)
  }, [message, onDismiss])

  if (!message) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex items-start gap-3 max-w-sm rounded-lg border border-red-500/50 bg-red-950/90 px-4 py-3 shadow-xl backdrop-blur-sm">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
      <p className="flex-1 text-sm text-red-200">{message}</p>
      <button
        onClick={onDismiss}
        className="text-red-400 hover:text-red-200 transition-colors"
        aria-label="Dismiss error"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

import { AlertCircle } from 'lucide-react'

export default function ConfirmModal({ title, message, confirmLabel = 'Confirm', onConfirm, onCancel, danger = false }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-xl border border-gray-700 bg-gray-900 p-6 shadow-2xl">
        <div className="mb-4 flex items-start gap-3">
          <AlertCircle className={`mt-0.5 h-5 w-5 shrink-0 ${danger ? 'text-red-400' : 'text-yellow-400'}`} />
          <div>
            <h3 className="font-semibold text-gray-100">{title}</h3>
            {message && <p className="mt-1 text-sm text-gray-400">{message}</p>}
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-md px-4 py-2 text-sm font-medium text-gray-400 hover:bg-gray-800 hover:text-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              danger
                ? 'bg-red-700 text-white hover:bg-red-600'
                : 'bg-blue-700 text-white hover:bg-blue-600'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

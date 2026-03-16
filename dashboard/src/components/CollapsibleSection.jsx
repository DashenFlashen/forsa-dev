import { useState } from 'react'
import { ChevronRight } from 'lucide-react'

export default function CollapsibleSection({ title, children }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 px-5 py-4">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 lg:hidden"
      >
        <ChevronRight
          className={`h-3.5 w-3.5 text-gray-500 transition-transform ${open ? 'rotate-90' : ''}`}
        />
        <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          {title}
        </h2>
      </button>
      <h2 className="mb-3 hidden text-xs font-semibold uppercase tracking-wider text-gray-500 lg:block">
        {title}
      </h2>
      <div className={`${open ? '' : 'hidden'} lg:!block`}>
        {children}
      </div>
    </div>
  )
}

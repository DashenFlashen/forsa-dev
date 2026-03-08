const CONFIGS = {
  running:  { dot: 'bg-green-400 animate-pulse', bg: 'bg-green-900/40',  text: 'text-green-300',  border: 'border-green-800/60' },
  stopped:  { dot: 'bg-gray-500',                bg: 'bg-gray-800/40',   text: 'text-gray-400',   border: 'border-gray-700/60' },
  crashed:  { dot: 'bg-red-400',                 bg: 'bg-red-900/40',    text: 'text-red-300',    border: 'border-red-800/60' },
  active:   { dot: 'bg-green-400',               bg: 'bg-green-900/30',  text: 'text-green-400',  border: 'border-green-800/40' },
  detached: { dot: 'bg-yellow-400',              bg: 'bg-yellow-900/30', text: 'text-yellow-400', border: 'border-yellow-800/40' },
  missing:  { dot: 'bg-red-400',                 bg: 'bg-red-900/30',    text: 'text-red-400',    border: 'border-red-800/40' },
}

export default function StatusBadge({ status }) {
  const cfg = CONFIGS[status] ?? CONFIGS.stopped
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${cfg.bg} ${cfg.text} ${cfg.border}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      {status}
    </span>
  )
}

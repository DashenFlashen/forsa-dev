function Bar({ label, value, max, unit }) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  const color = pct > 85 ? 'bg-red-500' : pct > 60 ? 'bg-yellow-500' : 'bg-green-500'
  return (
    <div className="flex items-center gap-3">
      <span className="w-28 shrink-0 text-sm text-gray-400">{label}</span>
      <div className="h-2 flex-1 overflow-hidden rounded bg-gray-700">
        <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-32 text-right text-sm text-gray-300">
        {value.toFixed(1)} / {max.toFixed(1)} {unit}
      </span>
    </div>
  )
}

export default function HealthBar({ health }) {
  if (!health) return null
  return (
    <div className="mb-6 rounded-lg border border-gray-800 bg-gray-900 p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
        System Health
      </h2>
      <div className="space-y-2">
        <Bar label={`CPU (${health.cpu_count} cores)`} value={health.cpu_percent} max={100} unit="%" />
        <Bar label="RAM" value={health.ram_used_gb} max={health.ram_total_gb} unit="GB" />
        <Bar label="Disk" value={health.disk_used_gb} max={health.disk_total_gb} unit="GB" />
      </div>
    </div>
  )
}

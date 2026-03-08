function Gauge({ label, value, max, unit }) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  const color =
    pct > 85 ? 'bg-red-500' :
    pct > 60 ? 'bg-yellow-500' :
    'bg-green-500'

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-400">{label}</span>
        <span className="text-xs tabular-nums text-gray-300">
          {value.toFixed(1)} / {max.toFixed(1)} {unit}
          <span className="ml-2 text-gray-500">({pct}%)</span>
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-gray-700">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default function HealthPanel({ health }) {
  if (!health) return null
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 px-5 py-4">
      <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-gray-500">
        System Health
      </h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Gauge label={`CPU (${health.cpu_count} cores)`} value={health.cpu_percent} max={100} unit="%" />
        <Gauge label="RAM" value={health.ram_used_gb} max={health.ram_total_gb} unit="GB" />
        <Gauge label="Disk" value={health.disk_used_gb} max={health.disk_total_gb} unit="GB" />
      </div>
    </div>
  )
}

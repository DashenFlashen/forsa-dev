import CollapsibleSection from './CollapsibleSection'

function Gauge({ label, value, max, unit }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0
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
      <div className="h-2 overflow-hidden rounded-full bg-gray-800">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color} ${pct > 85 ? 'theme-gauge-glow-red' : pct > 60 ? 'theme-gauge-glow-yellow' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default function HealthPanel({ health }) {
  if (!health) return null
  return (
    <CollapsibleSection title="System Health">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Gauge label={`CPU (${health.cpu_count} cores)`} value={health.cpu_percent} max={100} unit="%" />
        <Gauge label="RAM" value={health.ram_used_gb} max={health.ram_total_gb} unit="GB" />
        <Gauge label="Disk" value={health.disk_used_gb} max={health.disk_total_gb} unit="GB" />
      </div>
    </CollapsibleSection>
  )
}

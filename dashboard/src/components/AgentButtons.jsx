import { useState, useEffect, useRef } from 'react'
import { Terminal, ChevronDown, Wrench } from 'lucide-react'

export default function AgentButtons({ onSelectAgent }) {
  const [agents, setAgents] = useState([])
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    fetch('/api/agents')
      .then((r) => r.ok ? r.json() : [])
      .then(setAgents)
      .catch(() => {})
  }, [])

  // Poll every 10s
  useEffect(() => {
    const id = setInterval(() => {
      fetch('/api/agents')
        .then((r) => r.ok ? r.json() : [])
        .then(setAgents)
        .catch(() => {})
    }, 10000)
    return () => clearInterval(id)
  }, [])

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('click', handleClick, true)
    return () => document.removeEventListener('click', handleClick, true)
  }, [open])

  if (agents.length === 0) return null

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all duration-200 ${
          open
            ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-200 shadow-[0_0_20px_rgba(99,102,241,0.2)]'
            : 'bg-indigo-500/10 border-indigo-500/20 text-indigo-300 hover:bg-indigo-500/15 hover:border-indigo-500/30 hover:text-indigo-200 hover:-translate-y-px hover:shadow-[0_4px_20px_rgba(99,102,241,0.15)]'
        } border`}
      >
        <svg className={`h-3.5 w-3.5 transition-transform duration-300 ${open ? 'rotate-[20deg] scale-110' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3v1m0 16v1m-8-9H3m18 0h-1m-2.636-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707.707"/>
          <circle cx="12" cy="12" r="4"/>
        </svg>
        Agents
        <ChevronDown className={`h-3 w-3 opacity-50 transition-transform duration-200 ${open ? 'rotate-180 opacity-80' : ''}`} />
      </button>

      <div className={`absolute right-0 top-full mt-2 w-72 rounded-xl border border-indigo-500/15 bg-gradient-to-b from-gray-900 via-gray-900 to-gray-950 p-1.5 shadow-[0_20px_60px_rgba(0,0,0,0.5),0_0_40px_rgba(99,102,241,0.08)] transition-all duration-200 ${
        open
          ? 'opacity-100 translate-y-0 scale-100 pointer-events-auto'
          : 'opacity-0 -translate-y-2 scale-[0.96] pointer-events-none'
      } z-50`}>
        <div className="px-3 pt-2 pb-1 text-[0.65rem] font-semibold uppercase tracking-widest text-gray-500">
          Active Agents
        </div>
        {agents.map((agent, i) => (
          <div key={agent.name}>
            {i > 0 && <div className="mx-3 h-px bg-gradient-to-r from-transparent via-indigo-500/10 to-transparent" />}
            <button
              onClick={() => { onSelectAgent(agent); setOpen(false) }}
              className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-all duration-200 hover:translate-x-1 active:scale-[0.99] ${
                i === 0 ? 'hover:bg-blue-500/[0.06]' : 'hover:bg-purple-500/[0.06]'
              }`}
            >
              <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${
                i === 0
                  ? 'border-blue-500/20 bg-blue-500/10'
                  : 'border-purple-500/20 bg-purple-500/10'
              }`}>
                {i === 0
                  ? <Terminal className="h-4 w-4 text-blue-400" />
                  : <Wrench className="h-4 w-4 text-purple-400" />
                }
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-semibold text-gray-200">{agent.label}</div>
                <div className="text-xs text-gray-500">{agent.description} · {agent.cwd}</div>
              </div>
              <div className={`flex items-center gap-1 rounded px-1.5 py-0.5 text-[0.65rem] font-medium ${
                agent.ttyd === 'alive'
                  ? 'bg-green-500/10 text-green-400 border border-green-500/15'
                  : 'bg-red-500/10 text-red-400 border border-red-500/15'
              }`}>
                <span className={`h-1.5 w-1.5 rounded-full ${
                  agent.ttyd === 'alive' ? 'bg-green-400 animate-pulse' : 'bg-red-400'
                }`} />
                {agent.ttyd === 'alive' ? 'Live' : 'Down'}
              </div>
              <ChevronDown className="h-3.5 w-3.5 -rotate-90 text-gray-600 transition-all group-hover:translate-x-0.5 group-hover:text-gray-400" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function TerminalView({ env, host, onClose }) {
  const src = `http://${host}:${env.ttyd_port}`
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-2">
        <span className="font-mono text-sm text-gray-300">{env.name}</span>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-100"
          aria-label="Close terminal"
        >
          ✕
        </button>
      </div>
      <iframe
        src={src}
        className="flex-1 w-full border-0"
        title={`Terminal: ${env.name}`}
      />
    </div>
  )
}

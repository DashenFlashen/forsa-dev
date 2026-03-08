export default function TerminalView({ env, host, onClose }) {
  const src = env.ttyd_port ? `http://${host}:${env.ttyd_port}` : null
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
      {src ? (
        <iframe
          src={src}
          className="flex-1 w-full border-0"
          title={`Terminal: ${env.name}`}
        />
      ) : (
        <div className="flex flex-1 items-center justify-center text-gray-500">
          Terminal not available
        </div>
      )}
    </div>
  )
}

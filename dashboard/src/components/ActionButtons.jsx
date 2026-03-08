const STATUS_SHOW_SERVE = ['stopped', 'crashed']

export default function ActionButtons({ env, onAction, loading }) {
  const serverStatus = env.status.server

  const btnBase = 'rounded px-3 py-1 text-sm font-medium transition-opacity disabled:opacity-50'

  return (
    <div className="flex gap-2">
      {STATUS_SHOW_SERVE.includes(serverStatus) && (
        <button
          className={`${btnBase} bg-green-700 hover:bg-green-600`}
          disabled={loading}
          onClick={() => onAction(env.name, 'serve')}
        >
          {loading === 'serve' ? '...' : 'Serve'}
        </button>
      )}
      {serverStatus === 'running' && (
        <>
          <button
            className={`${btnBase} bg-gray-700 hover:bg-gray-600`}
            disabled={loading}
            onClick={() => onAction(env.name, 'stop')}
          >
            {loading === 'stop' ? '...' : 'Stop'}
          </button>
          <button
            className={`${btnBase} bg-blue-700 hover:bg-blue-600`}
            disabled={loading}
            onClick={() => onAction(env.name, 'restart')}
          >
            {loading === 'restart' ? '...' : 'Restart'}
          </button>
        </>
      )}
    </div>
  )
}

import { Play, Square, RefreshCw } from 'lucide-react'

const STATUS_SHOW_SERVE = ['stopped', 'crashed']

function ActionBtn({ icon: Icon, label, onClick, disabled, loading, colorClass }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className={`rounded-md p-2.5 lg:p-1.5 transition-colors disabled:opacity-50 ${colorClass}`}
    >
      {loading ? (
        <RefreshCw className="h-4 w-4 lg:h-3.5 lg:w-3.5 animate-spin" />
      ) : (
        <Icon className="h-4 w-4 lg:h-3.5 lg:w-3.5" />
      )}
    </button>
  )
}

export default function ActionButtons({ env, onAction, loading }) {
  const serverStatus = env.status.server

  return (
    <div className="flex items-center gap-1">
      {STATUS_SHOW_SERVE.includes(serverStatus) && (
        <ActionBtn
          icon={Play}
          label="Start server"
          onClick={() => onAction(env.user, env.name, 'serve')}
          disabled={!!loading}
          loading={loading === 'serve'}
          colorClass="text-green-400 hover:bg-green-900/40 hover:text-green-300"
        />
      )}
      {serverStatus === 'running' && (
        <>
          <ActionBtn
            icon={Square}
            label="Stop server"
            onClick={() => onAction(env.user, env.name, 'stop')}
            disabled={!!loading}
            loading={loading === 'stop'}
            colorClass="text-gray-400 hover:bg-gray-800 hover:text-gray-200"
          />
          <ActionBtn
            icon={RefreshCw}
            label="Restart server"
            onClick={() => onAction(env.user, env.name, 'restart')}
            disabled={!!loading}
            loading={loading === 'restart'}
            colorClass="text-blue-400 hover:bg-blue-900/40 hover:text-blue-300"
          />
        </>
      )}
    </div>
  )
}

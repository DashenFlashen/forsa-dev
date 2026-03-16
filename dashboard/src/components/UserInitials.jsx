export default function UserInitials({ user, className = "h-6 w-6" }) {
  const initials = user
    .split(/[-_\s]/)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
  return (
    <span
      title={user}
      className={`inline-flex items-center justify-center rounded-full bg-gray-700 text-xs font-medium text-gray-300 ${className}`}
    >
      {initials}
    </span>
  )
}

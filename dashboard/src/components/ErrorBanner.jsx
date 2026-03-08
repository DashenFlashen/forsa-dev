export default function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <div className="mb-4 rounded border border-red-500 bg-red-950 px-4 py-3 text-red-200">
      {message}
    </div>
  )
}

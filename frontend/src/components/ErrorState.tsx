interface Props {
  message: string
  onRetry?: () => void
}

export default function ErrorState({ message, onRetry }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-red-600">
      <span className="text-3xl mb-2">!</span>
      <p className="text-sm mb-3">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-1.5 bg-red-50 text-red-700 rounded text-sm hover:bg-red-100"
        >
          Retry
        </button>
      )}
    </div>
  )
}

import { useState, useMemo } from 'react'
import { useHooks } from '../hooks/useApi'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorState from '../components/ErrorState'
import EmptyState from '../components/EmptyState'

export default function Hooks() {
  const { data, isLoading, error, refetch } = useHooks()
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null)

  const grouped = useMemo(() => {
    if (!data) return {}
    const g: Record<string, typeof data.hooks> = {}
    for (const h of data.hooks) {
      const ev = h.metadata.lifecycle_event
      if (!g[ev]) g[ev] = []
      g[ev].push(h)
    }
    return g
  }, [data])

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorState message={(error as Error).message} onRetry={refetch} />
  if (!data || data.hooks.length === 0) return <EmptyState title="No hooks registered" />

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Hooks</h1>
      <p className="text-gray-500 text-sm mb-4">{data.total} hooks registered</p>

      <div className="space-y-3">
        {Object.entries(grouped)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([event, hooks]) => {
            const isOpen = expandedGroup === event
            return (
              <div key={event} className="bg-white rounded-lg shadow">
                <button
                  onClick={() => setExpandedGroup(isOpen ? null : event)}
                  className="w-full flex items-center justify-between p-4 text-left"
                >
                  <span className="font-medium">{event}</span>
                  <span className="text-gray-400 text-sm">
                    {hooks.length} hooks {isOpen ? '▲' : '▼'}
                  </span>
                </button>
                {isOpen && (
                  <div className="px-4 pb-4 border-t border-gray-100">
                    {[...hooks]
                      .sort((a, b) => a.metadata.priority - b.metadata.priority)
                      .map((h) => (
                        <div key={h.hook_id} className="py-2 border-b border-gray-50 last:border-0 text-sm">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{h.metadata.name}</span>
                            <span className="text-xs text-gray-400">
                              priority {h.metadata.priority}
                            </span>
                            <span className={`text-xs px-1.5 rounded ${h.metadata.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                              {h.metadata.enabled ? 'enabled' : 'disabled'}
                            </span>
                          </div>
                          <p className="text-gray-500 text-xs mt-0.5">{h.metadata.description}</p>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )
          })}
      </div>
    </div>
  )
}

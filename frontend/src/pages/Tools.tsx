import { useState } from 'react'
import { useTools } from '../hooks/useApi'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorState from '../components/ErrorState'
import EmptyState from '../components/EmptyState'

const RISK_COLORS: Record<string, string> = {
  LOW: 'bg-green-100 text-green-700',
  MEDIUM: 'bg-yellow-100 text-yellow-700',
  HIGH: 'bg-orange-100 text-orange-700',
  CRITICAL: 'bg-red-100 text-red-700',
}

export default function Tools() {
  const { data, isLoading, error, refetch } = useTools()
  const [expanded, setExpanded] = useState<string | null>(null)

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorState message={(error as Error).message} onRetry={refetch} />
  if (!data || data.tools.length === 0) return <EmptyState title="No tools registered" />

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Tools</h1>
      <p className="text-gray-500 text-sm mb-4">{data.total} tools registered</p>

      <div className="space-y-3">
        {data.tools.map((t) => {
          const isOpen = expanded === t.id
          return (
            <div key={t.id} className="bg-white rounded-lg shadow">
              <button
                onClick={() => setExpanded(isOpen ? null : t.id)}
                className="w-full flex items-center justify-between p-4 text-left"
              >
                <div className="flex items-center gap-3">
                  <span className="font-medium">{t.metadata.name}</span>
                  <span className={`text-xs px-1.5 rounded ${RISK_COLORS[t.metadata.risk_level] || 'bg-gray-100'}`}>
                    {t.metadata.risk_level}
                  </span>
                  <span className="text-xs text-gray-400">{t.metadata.permission}</span>
                </div>
                <span className="text-gray-400">{isOpen ? '▲' : '▼'}</span>
              </button>
              {isOpen && (
                <div className="px-4 pb-4 border-t border-gray-100 pt-3 text-sm space-y-2">
                  <p>{t.metadata.description}</p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div><span className="text-gray-500">Version:</span> {t.metadata.version}</div>
                    <div><span className="text-gray-500">Timeout:</span> {t.metadata.timeout_seconds}s</div>
                    <div><span className="text-gray-500">Enabled:</span> {t.metadata.enabled ? 'Yes' : 'No'}</div>
                  </div>
                  {t.metadata.input_schema && (
                    <div>
                      <span className="text-gray-500 text-xs">Input Schema</span>
                      <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-auto">
                        {JSON.stringify(t.metadata.input_schema, null, 2)}
                      </pre>
                    </div>
                  )}
                  {t.metadata.output_schema && (
                    <div>
                      <span className="text-gray-500 text-xs">Output Schema</span>
                      <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-auto">
                        {JSON.stringify(t.metadata.output_schema, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

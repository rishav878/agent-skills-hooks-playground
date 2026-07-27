import { useState } from 'react'
import { useSkills } from '../hooks/useApi'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorState from '../components/ErrorState'
import EmptyState from '../components/EmptyState'

export default function Skills() {
  const { data, isLoading, error, refetch } = useSkills()
  const [expanded, setExpanded] = useState<string | null>(null)

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorState message={(error as Error).message} onRetry={refetch} />
  if (!data || data.skills.length === 0) return <EmptyState title="No skills registered" />

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Skills</h1>
      <p className="text-gray-500 text-sm mb-4">{data.total} skills registered</p>

      <div className="space-y-3">
        {data.skills.map((s) => {
          const isOpen = expanded === s.id
          return (
            <div key={s.id} className="bg-white rounded-lg shadow">
              <button
                onClick={() => setExpanded(isOpen ? null : s.id)}
                className="w-full flex items-center justify-between p-4 text-left"
              >
                <div>
                  <span className="font-medium">{s.metadata.name}</span>
                  <span className="text-gray-400 ml-2 text-sm">v{s.metadata.version}</span>
                </div>
                <span className="text-gray-400">{isOpen ? '▲' : '▼'}</span>
              </button>
              {isOpen && (
                <div className="px-4 pb-4 border-t border-gray-100 pt-3 text-sm space-y-2">
                  <p>{s.metadata.description}</p>
                  {s.metadata.allowed_tools && (
                    <p><span className="text-gray-500">Tools:</span> {s.metadata.allowed_tools.join(', ')}</p>
                  )}
                  {s.metadata.input_schema && (
                    <div>
                      <span className="text-gray-500">Input Schema</span>
                      <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-auto">
                        {JSON.stringify(s.metadata.input_schema, null, 2)}
                      </pre>
                    </div>
                  )}
                  {s.metadata.output_schema && (
                    <div>
                      <span className="text-gray-500">Output Schema</span>
                      <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-auto">
                        {JSON.stringify(s.metadata.output_schema, null, 2)}
                      </pre>
                    </div>
                  )}
                  <p className="text-xs text-gray-400">ID: {s.id}</p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

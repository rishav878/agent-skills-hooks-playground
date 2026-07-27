import { useNavigate } from 'react-router-dom'
import { useRuns } from '../hooks/useApi'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorState from '../components/ErrorState'
import EmptyState from '../components/EmptyState'

export default function RunHistory() {
  const { data, isLoading, error, refetch } = useRuns(100)
  const navigate = useNavigate()

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorState message={(error as Error).message} onRetry={refetch} />
  if (!data || data.runs.length === 0) return <EmptyState title="No runs yet" description="Run an agent in the Playground" />

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Run History</h1>
      <p className="text-gray-500 text-sm mb-4">{data.total} runs total</p>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left">
            <tr>
              <th className="px-4 py-2 font-medium text-gray-500">Run ID</th>
              <th className="px-4 py-2 font-medium text-gray-500">Status</th>
              <th className="px-4 py-2 font-medium text-gray-500">Skill</th>
              <th className="px-4 py-2 font-medium text-gray-500">Time</th>
              <th className="px-4 py-2 font-medium text-gray-500">Retries</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {data.runs.map((r) => (
              <tr key={r.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{r.id.slice(0, 8)}...</td>
                <td className="px-4 py-2">
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                    r.status === 'completed' ? 'bg-green-100 text-green-700' :
                    r.status === 'failed' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {r.status}
                  </span>
                </td>
                <td className="px-4 py-2">{r.selected_skill || '—'}</td>
                <td className="px-4 py-2 text-xs text-gray-400">
                  {r.created_at ? r.created_at.slice(11, 19) : '—'}
                </td>
                <td className="px-4 py-2 text-xs">{r.retry_count}</td>
                <td className="px-4 py-2">
                  <button
                    onClick={() => navigate(`/runs/${r.id}`)}
                    className="text-blue-600 hover:underline text-xs"
                  >
                    Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

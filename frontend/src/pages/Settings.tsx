import { useHealth } from '../hooks/useApi'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorState from '../components/ErrorState'

export default function Settings() {
  const { data: health, isLoading, error } = useHealth()

  if (isLoading) return <LoadingSpinner text="Loading..." />
  if (error) return <ErrorState message="Cannot reach backend" />

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Settings</h1>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="font-semibold mb-3">Backend Connection</h2>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-500">Status</dt>
            <dd className="font-medium">{health?.status}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Version</dt>
            <dd className="font-medium">{health?.version}</dd>
          </div>

        </dl>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold mb-3">API</h2>
        <p className="text-sm text-gray-500 mb-2">
          All API requests require an <code className="bg-gray-100 px-1 rounded">X-API-Key</code> header.
        </p>
        <p className="text-sm text-gray-500">
          API base URL: <code className="bg-gray-100 px-1 rounded">/api/v1</code>
        </p>
      </div>
    </div>
  )
}

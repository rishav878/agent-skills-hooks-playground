import { useSkills, useHooks, useTools, useRuns, useHealth } from '../hooks/useApi'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorState from '../components/ErrorState'

export default function Dashboard() {
  const { data: health, isLoading: hl, error: he } = useHealth()
  const { data: skills } = useSkills()
  const { data: hooks } = useHooks()
  const { data: tools } = useTools()
  const { data: runs } = useRuns(5)

  if (hl) return <LoadingSpinner text="Connecting to backend..." />
  if (he) return <ErrorState message="Cannot reach backend" />

  const metrics = [
    { label: 'Skills', value: skills?.total ?? 0 },
    { label: 'Hooks', value: hooks?.total ?? 0 },
    { label: 'Tools', value: tools?.total ?? 0 },
    { label: 'Recent Runs', value: runs?.total ?? 0 },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Dashboard</h1>
      <p className="text-gray-500 text-sm mb-6">
        Backend: {health?.status} v{health?.version}
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {metrics.map((m) => (
          <div key={m.label} className="bg-white rounded-lg shadow p-4">
            <div className="text-2xl font-bold">{m.value}</div>
            <div className="text-sm text-gray-500">{m.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-3">Skills</h2>
          {skills?.skills.map((s) => (
            <div key={s.id} className="text-sm py-1 border-b border-gray-100 last:border-0">
              <span className="font-medium">{s.metadata.name}</span>
              <span className="text-gray-400 ml-2">v{s.metadata.version}</span>
            </div>
          ))}
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-3">Recent Runs</h2>
          {runs && runs.runs.length > 0 ? (
            runs.runs.map((r) => (
              <div key={r.id} className="text-sm py-1 border-b border-gray-100 last:border-0 flex justify-between">
                <span>
                  <span className="font-mono text-xs">{r.id.slice(0, 8)}</span>
                  <span className="ml-2">{r.selected_skill || '—'}</span>
                </span>
                <span className="text-gray-500">{r.status}</span>
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-400">No runs yet</p>
          )}
        </div>
      </div>
    </div>
  )
}

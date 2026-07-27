import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useRun, useRunEvents } from '../hooks/useApi'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorState from '../components/ErrorState'
import EventTimeline from '../components/EventTimeline'
import EventDetails from '../components/EventDetails'

export default function RunDetails() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: run, isLoading: runLoading, error: runError } = useRun(id!)
  const { data: eventsData, isLoading: evLoading } = useRunEvents(id!)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  if (runLoading || evLoading) return <LoadingSpinner />
  if (runError) return <ErrorState message={(runError as Error).message} />

  if (!run) return <ErrorState message="Run not found" />

  const events = eventsData?.events ?? []
  const selectedEvent = events.find((e) => e.event_id === selectedId) || null

  return (
    <div>
      <button
        onClick={() => navigate('/runs')}
        className="text-sm text-blue-600 hover:underline mb-4 inline-block"
      >
        &larr; Back to Runs
      </button>

      <h1 className="text-2xl font-bold mb-4">Run Details</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-gray-500">Run ID</div>
          <div className="font-mono text-sm">{run.id}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-gray-500">Status</div>
          <div className="text-sm font-medium">{run.status}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-gray-500">Skill</div>
          <div className="text-sm">{run.selected_skill || '—'}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-gray-500">Trace ID</div>
          <div className="font-mono text-xs">{run.trace_id}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-gray-500">Retries</div>
          <div className="text-sm">{run.retry_count}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-xs text-gray-500">Created</div>
          <div className="text-sm">{run.created_at}</div>
        </div>
      </div>

      {run.error && (
        <div className="mb-6 p-3 bg-red-50 text-red-700 rounded text-sm">
          Error: {run.error}
        </div>
      )}

      <div className="mb-6 bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold mb-2">Input</h2>
        <pre className="text-sm bg-gray-50 p-3 rounded overflow-auto max-h-40">
          {run.input}
        </pre>
      </div>

      {run.output && (
        <div className="mb-6 bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-2">Output</h2>
          <pre className="text-sm bg-gray-50 p-3 rounded overflow-auto max-h-60">
            {(() => {
              try { return JSON.stringify(JSON.parse(run.output), null, 2) }
              catch { return run.output }
            })()}
          </pre>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white rounded-lg shadow">
          <div className="p-3 border-b border-gray-100 font-medium">Events ({events.length})</div>
          <div className="p-3 max-h-96 overflow-auto">
            <EventTimeline
              events={events}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4 overflow-auto max-h-96">
          <EventDetails event={selectedEvent} />
        </div>
      </div>
    </div>
  )
}

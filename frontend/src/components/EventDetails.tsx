import type { AgentEvent } from '../api/types'

interface Props {
  event: AgentEvent | null
}

export default function EventDetails({ event }: Props) {
  if (!event) {
    return (
      <div className="text-sm text-gray-400 text-center py-8">
        Click an event to inspect
      </div>
    )
  }

  const rows: [string, string][] = [
    ['Event ID', event.event_id],
    ['Run ID', event.run_id],
    ['Trace ID', event.trace_id],
    ['Type', event.event_type],
    ['Component', event.component],
    ['Status', event.status],
    ['Timestamp', event.timestamp],
    ['Duration', event.duration_ms ? `${event.duration_ms}ms` : '—'],
  ]

  return (
    <div className="text-sm space-y-3">
      <h3 className="font-semibold text-base">Event Details</h3>
      <table className="w-full text-xs">
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k} className="border-b border-gray-100">
              <td className="py-1 pr-3 text-gray-500 whitespace-nowrap">{k}</td>
              <td className="py-1 font-mono break-all">{v}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {event.error && (
        <div>
          <h4 className="font-medium text-red-600 mb-1">Error</h4>
          <pre className="text-xs bg-red-50 p-2 rounded overflow-auto max-h-32">
            {event.error}
          </pre>
        </div>
      )}

      {event.input && (
        <div>
          <h4 className="font-medium text-gray-700 mb-1">Input</h4>
          <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-40">
            {JSON.stringify(event.input, null, 2)}
          </pre>
        </div>
      )}

      {event.output && (
        <div>
          <h4 className="font-medium text-gray-700 mb-1">Output</h4>
          <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-40">
            {JSON.stringify(event.output, null, 2)}
          </pre>
        </div>
      )}

      {event.metadata && Object.keys(event.metadata).length > 0 && (
        <div>
          <h4 className="font-medium text-gray-700 mb-1">Metadata</h4>
          <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-32">
            {JSON.stringify(event.metadata, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

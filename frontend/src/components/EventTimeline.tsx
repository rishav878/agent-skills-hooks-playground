import type { AgentEvent } from '../api/types'

interface Props {
  events: AgentEvent[]
  selectedId: string | null
  onSelect: (id: string) => void
}

const STATUS_ICONS: Record<string, string> = {
  running: '',
  completed: '✓',
  failed: '✗',
  blocked: '!',
  skipped: '→',
  waiting_approval: '⌛',
  approved: '✓',
}

export default function EventTimeline({ events, selectedId, onSelect }: Props) {
  if (events.length === 0) {
    return (
      <div className="text-sm text-gray-400 text-center py-8">
        No events yet
      </div>
    )
  }

  return (
    <div className="space-y-0.5 overflow-auto max-h-full">
      {events.map((ev, i) => {
        const icon = STATUS_ICONS[ev.status] || '?'
        const isSelected = ev.event_id === selectedId
        const ts = ev.timestamp ? ev.timestamp.slice(11, 19) : ''
        return (
          <button
            key={ev.event_id}
            onClick={() => onSelect(ev.event_id)}
            className={`w-full text-left px-3 py-1.5 text-xs border-l-2 transition-colors ${
              isSelected
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:bg-gray-50'
            }`}
          >
            <span className="font-mono text-gray-400 mr-2">{ts}</span>
            <span className="mr-1">{icon}</span>
            <span className="font-medium">{ev.event_type}</span>
            <span className="text-gray-400 ml-1">({ev.component})</span>
          </button>
        )
      })}
    </div>
  )
}

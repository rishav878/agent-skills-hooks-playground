import type { NodeStatus } from '../api/types'

const colors: Record<NodeStatus, string> = {
  PENDING: 'bg-gray-100 text-gray-600',
  RUNNING: 'bg-blue-100 text-blue-700',
  COMPLETED: 'bg-green-100 text-green-700',
  FAILED: 'bg-red-100 text-red-700',
  BLOCKED: 'bg-orange-100 text-orange-700',
  WAITING_FOR_APPROVAL: 'bg-yellow-100 text-yellow-700',
}

export default function NodeStatusBadge({ status }: { status: NodeStatus }) {
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-600'}`}
    >
      {status.replace(/_/g, ' ')}
    </span>
  )
}

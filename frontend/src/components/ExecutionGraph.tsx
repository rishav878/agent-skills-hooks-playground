import { useMemo } from 'react'
import ReactFlow, {
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from 'reactflow'
import 'reactflow/dist/style.css'
import type { AgentEvent, NodeStatus } from '../api/types'

const STATUS_COLORS: Record<NodeStatus, { bg: string; border: string }> = {
  PENDING: { bg: '#f3f4f6', border: '#d1d5db' },
  RUNNING: { bg: '#dbeafe', border: '#3b82f6' },
  COMPLETED: { bg: '#d1fae5', border: '#10b981' },
  FAILED: { bg: '#fee2e2', border: '#ef4444' },
  BLOCKED: { bg: '#ffedd5', border: '#f97316' },
  WAITING_FOR_APPROVAL: { bg: '#fef9c3', border: '#eab308' },
}

function statusFromEvents(events: AgentEvent[], nodeType: string): NodeStatus {
  const matching = events.filter(
    (e) => e.component === nodeType || e.event_type.startsWith(nodeType),
  )
  if (matching.length === 0) return 'PENDING'
  const latest = matching[matching.length - 1]
  switch (latest.status) {
    case 'running':
      return 'RUNNING'
    case 'completed':
    case 'approved':
      return 'COMPLETED'
    case 'failed':
      return 'FAILED'
    case 'blocked':
      return 'BLOCKED'
    case 'waiting_approval':
      return 'WAITING_FOR_APPROVAL'
    default:
      return 'PENDING'
  }
}

const NODE_DEFS = [
  { id: 'request', label: 'Request Received', type: 'request' },
  { id: 'hooks-before', label: 'Before Request Hooks', type: 'hook' },
  { id: 'classify', label: 'Skill Selection', type: 'skill' },
  { id: 'hooks-before-skill', label: 'Before Skill Hooks', type: 'hook' },
  { id: 'execute-skill', label: 'Execute Skill', type: 'skill' },
  { id: 'tool-router', label: 'Tool Router', type: 'tool' },
  { id: 'hooks-before-tool', label: 'Before Tool Hooks', type: 'hook' },
  { id: 'permission', label: 'Permission Check', type: 'tool' },
  { id: 'approval', label: 'Approval Check', type: 'tool' },
  { id: 'execute-tool', label: 'Execute Tool', type: 'tool' },
  { id: 'hooks-after-tool', label: 'After Tool Hooks', type: 'hook' },
  { id: 'validate', label: 'Validate Result', type: 'runtime' },
  { id: 'hooks-after-skill', label: 'After Skill Hooks', type: 'hook' },
  { id: 'generate', label: 'Generate Response', type: 'agent' },
  { id: 'hooks-before-response', label: 'Before Response Hooks', type: 'hook' },
  { id: 'hooks-after-request', label: 'After Request Hooks', type: 'hook' },
  { id: 'persist', label: 'Persist Run', type: 'runtime' },
]

function CustomNode({ data }: NodeProps) {
  const { label, status } = data as { label: string; status: NodeStatus }
  const colors = STATUS_COLORS[status] || STATUS_COLORS.PENDING
  return (
    <div
      className="px-3 py-2 rounded shadow-sm border-2 text-xs font-medium min-w-[120px] text-center"
      style={{ backgroundColor: colors.bg, borderColor: colors.border }}
    >
      <Handle type="target" position={Position.Top} />
      {label}
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}

const nodeTypes = { custom: CustomNode }

interface Props {
  events: AgentEvent[]
  onNodeClick: (eventType: string) => void
}

export default function ExecutionGraph({ events, onNodeClick }: Props) {
  const { nodes, edges } = useMemo(() => {
    const ns: Node[] = NODE_DEFS.map((def, i) => ({
      id: def.id,
      type: 'custom',
      position: { x: 200, y: i * 70 + 20 },
      data: {
        label: def.label,
        status: statusFromEvents(events, def.type),
      },
    }))
    const es: Edge[] = []
    for (let i = 0; i < ns.length - 1; i++) {
      es.push({
        id: `e-${ns[i].id}-${ns[i + 1].id}`,
        source: ns[i].id,
        target: ns[i + 1].id,
        style: { stroke: '#94a3b8' },
        animated: events.some(
          (e) =>
            e.status === 'running' &&
            (e.component === NODE_DEFS[i].type ||
              e.event_type.startsWith(NODE_DEFS[i].type)),
        ),
      })
    }
    return { nodes: ns, edges: es }
  }, [events])

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
        onNodeClick={(_e, node) => {
          const def = NODE_DEFS.find((d) => d.id === node.id)
          if (def) onNodeClick(def.type)
        }}
      />
    </div>
  )
}

export interface AgentEvent {
  event_id: string
  run_id: string
  trace_id: string
  timestamp: string
  event_type: string
  component: string
  status: string
  duration_ms: number | null
  input: Record<string, unknown> | string | null
  output: Record<string, unknown> | string | null
  error: string | null
  metadata: Record<string, unknown> | null
}

export interface RunSummary {
  id: string
  trace_id: string
  status: string
  selected_skill: string | null
  error: string | null
  retry_count: number
  created_at: string
  updated_at: string | null
}

export interface RunDetail {
  id: string
  trace_id: string
  status: string
  input: string
  output: string | null
  selected_skill: string | null
  error: string | null
  retry_count: number
  created_at: string
  updated_at: string | null
}

export interface SkillMetadata {
  name: string
  description: string
  version: string
  input_schema: Record<string, unknown> | null
  output_schema: Record<string, unknown> | null
  allowed_tools: string[] | null
  enabled: boolean
}

export interface Skill {
  id: string
  metadata: SkillMetadata
}

export interface HookMetadata {
  name: string
  description: string
  lifecycle_event: string
  priority: number
  enabled: boolean
  metadata: Record<string, unknown>
}

export interface Hook {
  hook_id: string
  metadata: HookMetadata
}

export interface ToolMetadata {
  name: string
  description: string
  version: string
  risk_level: string
  permission: string
  timeout_seconds: number
  enabled: boolean
  input_schema: Record<string, unknown> | null
  output_schema: Record<string, unknown> | null
  metadata: Record<string, unknown>
}

export interface Tool {
  id: string
  metadata: ToolMetadata
}

export interface AgentRunRequest {
  task: string
  parameters?: Record<string, unknown>
}

export interface AgentRunResponse {
  run_id: string
  trace_id: string | null
  task: string | null
  skill_used: string | null
  result: Record<string, unknown> | string | unknown[] | null
  status: string
  error: string | null
  retry_count: number
  events: EventSummary[]
}

export interface EventSummary {
  event_id: string
  event_type: string
  component: string
  status: string
  timestamp: string
}

export type NodeStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'BLOCKED'
  | 'WAITING_FOR_APPROVAL'

export interface FlowNode {
  id: string
  label: string
  status: NodeStatus
  event: AgentEvent | null
}

export interface ApproveResponse {
  run_id: string
  approval_id: string
  status: string
  result: Record<string, unknown> | string | unknown[] | null
  error: string | null
  events: EventSummary[]
}

export interface CancelResponse {
  run_id: string
  approval_id: string
  status: string
}

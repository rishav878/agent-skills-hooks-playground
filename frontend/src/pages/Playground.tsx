import { useState, useCallback, useRef, useEffect } from 'react'
import ExecutionGraph from '../components/ExecutionGraph'
import EventTimeline from '../components/EventTimeline'
import EventDetails from '../components/EventDetails'
import { useRunAgent } from '../hooks/useApi'
import { useWebSocket } from '../api/websocket'
import { api } from '../api/client'
import type { AgentEvent } from '../api/types'

export default function Playground() {
  const [task, setTask] = useState('')
  const [runId, setRunId] = useState<string | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [waitingApproval, setWaitingApproval] = useState(false)
  const [approvalError, setApprovalError] = useState<string | null>(null)
  const { events, connectionState, connect, disconnect, clearEvents } = useWebSocket()
  const runAgent = useRunAgent()
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  const selectedEvent = events.find((e) => e.event_id === selectedEventId) || null

  useEffect(() => {
    return () => {
      disconnect()
      if (pollTimer.current) clearInterval(pollTimer.current)
    }
  }, [disconnect])

  // Watch for approval_required events to show the approval dialog
  useEffect(() => {
    const hasApprovalEvent = events.some(
      (e) => e.event_type === 'approval_required' && e.status === 'waiting_approval',
    )
    setWaitingApproval(hasApprovalEvent)
  }, [events])

  const handleRun = useCallback(async () => {
    if (!task.trim()) return
    clearEvents()
    setRunId(null)
    setSelectedEventId(null)
    setWaitingApproval(false)
    setApprovalError(null)
    if (pollTimer.current) clearInterval(pollTimer.current)

    try {
      const result = await runAgent.mutateAsync({ task })
      setRunId(result.run_id)
      connect(result.run_id)
    } catch {
      // error handled by mutation state
    }
  }, [task, runAgent, connect, clearEvents])

  const handleApprove = useCallback(async () => {
    if (!runId) return
    setApprovalError(null)
    try {
      const result = await api.approveRun(runId)
      setWaitingApproval(false)
      // Refresh events from the approval response
      if (result.events?.length) {
        for (const ev of result.events) {
          const event: AgentEvent = {
            event_id: ev.event_id,
            run_id: runId,
            trace_id: '',
            timestamp: ev.timestamp,
            event_type: ev.event_type,
            component: ev.component,
            status: ev.status,
            duration_ms: null,
            input: null,
            output: null,
            error: null,
            metadata: null,
          }
          // Append via WebSocket-like mechanism — the WebSocket will also deliver these
          // We just let the existing events accumulate
        }
      }
    } catch (err) {
      setApprovalError((err as Error).message)
    }
  }, [runId])

  const handleDeny = useCallback(async () => {
    if (!runId) return
    setApprovalError(null)
    try {
      await api.cancelRun(runId)
      setWaitingApproval(false)
    } catch (err) {
      setApprovalError((err as Error).message)
    }
  }, [runId])

  const handleNodeClick = useCallback((componentType: string) => {
    const found = events.find((e) => e.component === componentType)
    if (found) setSelectedEventId(found.event_id)
  }, [events])

  return (
    <div className="h-full flex flex-col">
      <h1 className="text-2xl font-bold mb-4">Playground</h1>

      {/* Input row */}
      <div className="flex gap-3 mb-4">
        <input
          className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm"
          placeholder="Enter a task for the agent..."
          value={task}
          onChange={(e) => setTask(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleRun()}
          disabled={runAgent.isPending}
        />
        <button
          onClick={handleRun}
          disabled={runAgent.isPending || !task.trim()}
          className="px-5 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {runAgent.isPending ? 'Running...' : 'Run'}
        </button>
      </div>

      {runAgent.isError && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded text-sm">
          Run failed: {(runAgent.error as Error).message}
        </div>
      )}

      {approvalError && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded text-sm">
          Approval error: {approvalError}
        </div>
      )}

      {/* Main playground area */}
      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
        {/* Left: task run info + approval dialog */}
        <div className="col-span-3 bg-white rounded-lg shadow p-3 flex flex-col gap-3 overflow-auto">
          {runId && (
            <>
              <div>
                <span className="text-xs text-gray-500">Run ID</span>
                <div className="font-mono text-xs">{runId}</div>
              </div>
              <div>
                <span className="text-xs text-gray-500">WebSocket</span>
                <div className="text-xs">{connectionState}</div>
              </div>
              <div>
                <span className="text-xs text-gray-500">Events</span>
                <div className="text-xs font-medium">{events.length}</div>
              </div>
              {runAgent.data && (
                <>
                  <div>
                    <span className="text-xs text-gray-500">Skill</span>
                    <div className="text-sm font-medium">{runAgent.data.skill_used || '—'}</div>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">Status</span>
                    <div className="text-sm">{runAgent.data.status}</div>
                  </div>
                  {runAgent.data.error && (
                    <div className="text-red-600 text-xs">{runAgent.data.error}</div>
                  )}
                </>
              )}

              {/* Approval dialog */}
              {waitingApproval && (
                <div className="mt-2 p-3 bg-yellow-50 border border-yellow-300 rounded-lg">
                  <div className="text-sm font-semibold text-yellow-800 mb-2">
                    Approval Required
                  </div>
                  <div className="text-xs text-yellow-700 mb-3">
                    A high-risk tool is waiting for your decision.
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={handleApprove}
                      className="flex-1 px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded hover:bg-green-700"
                    >
                      Approve
                    </button>
                    <button
                      onClick={handleDeny}
                      className="flex-1 px-3 py-1.5 bg-red-600 text-white text-xs font-medium rounded hover:bg-red-700"
                    >
                      Deny
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
          {!runId && (
            <div className="text-sm text-gray-400 text-center py-8">
              Enter a task and click Run
            </div>
          )}
        </div>

        {/* Center: React Flow graph */}
        <div className="col-span-6 bg-white rounded-lg shadow min-h-0" style={{ height: '100%' }}>
          <ExecutionGraph events={events} onNodeClick={handleNodeClick} />
        </div>

        {/* Right: selected event details */}
        <div className="col-span-3 bg-white rounded-lg shadow p-3 overflow-auto">
          <EventDetails event={selectedEvent} />
        </div>
      </div>

      {/* Bottom: Event timeline */}
      <div className="mt-4 bg-white rounded-lg shadow" style={{ maxHeight: '180px' }}>
        <div className="p-2 border-b border-gray-100 text-sm font-medium">Event Timeline</div>
        <div className="overflow-auto" style={{ maxHeight: '140px' }}>
          <EventTimeline
            events={events}
            selectedId={selectedEventId}
            onSelect={setSelectedEventId}
          />
        </div>
      </div>
    </div>
  )
}

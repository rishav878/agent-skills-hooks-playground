import { useCallback, useEffect, useRef, useState } from 'react'
import type { AgentEvent } from './types'

const WS_BASE =
  window.location.protocol === 'https:'
    ? `wss://${window.location.host}/api/v1/runs/ws`
    : `ws://${window.location.host}/api/v1/runs/ws`

type ConnectionState = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED'

interface UseWebSocketReturn {
  events: AgentEvent[]
  connectionState: ConnectionState
  connect: (runId: string) => void
  disconnect: () => void
  clearEvents: () => void
}

export function useWebSocket(): UseWebSocketReturn {
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [connectionState, setConnectionState] =
    useState<ConnectionState>('DISCONNECTED')
  const wsRef = useRef<WebSocket | null>(null)
  const runIdRef = useRef<string | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = useRef(0)

  const clearEvents = useCallback(() => setEvents([]), [])

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }
    reconnectAttempts.current = 0
    runIdRef.current = null
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.onerror = null
      wsRef.current.onmessage = null
      wsRef.current.close()
      wsRef.current = null
    }
    setConnectionState('DISCONNECTED')
  }, [])

  const connect = useCallback(
    (runId: string) => {
      disconnect()
      runIdRef.current = runId
      reconnectAttempts.current = 0
      _open(runId)
    },
    [disconnect],
  )

  function _open(runId: string) {
    setConnectionState('CONNECTING')
    const ws = new WebSocket(`${WS_BASE}/${runId}`)
    wsRef.current = ws

    ws.onopen = () => {
      setConnectionState('CONNECTED')
      reconnectAttempts.current = 0
    }

    ws.onmessage = (msg: MessageEvent) => {
      try {
        const event: AgentEvent = JSON.parse(msg.data)
        setEvents((prev) => [...prev, event])
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = () => {
      setConnectionState('DISCONNECTED')
      wsRef.current = null
      // auto-reconnect up to 5 times
      if (runIdRef.current && reconnectAttempts.current < 5) {
        reconnectAttempts.current++
        const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 10000)
        reconnectTimer.current = setTimeout(
          () => _open(runIdRef.current!),
          delay,
        )
      }
    }

    ws.onerror = () => {
      ws.close()
    }
  }

  useEffect(() => {
    return () => disconnect()
  }, [disconnect])

  return { events, connectionState, connect, disconnect, clearEvents }
}

import { useCallback, useEffect, useRef, useState } from 'react'

export type Role = 'user' | 'assistant'
export type AgentName = 'grocery' | 'events' | 'todos' | 'orchestrator' | 'system'

export interface Message {
  id: string
  role: Role
  text: string
  agent?: AgentName
  timestamp: Date
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

const BACKEND_WS = (userId: string) =>
  `ws://localhost:8000/ws/${encodeURIComponent(userId)}`

export function useChat(userId: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const [isThinking, setIsThinking] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const addMessage = useCallback(
    (role: Role, text: string, agent?: AgentName) => {
      setMessages(prev => [
        ...prev,
        { id: crypto.randomUUID(), role, text, agent, timestamp: new Date() },
      ])
    },
    []
  )

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setStatus('connecting')
    const ws = new WebSocket(BACKEND_WS(userId))
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('connected')
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    }

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        setIsThinking(false)
        if (payload.type === 'response') {
          addMessage('assistant', payload.message, payload.agent_called ?? 'orchestrator')
        } else if (payload.type === 'error') {
          addMessage('assistant', `Error: ${payload.message}`, 'system')
        }
      } catch {
        // ignore malformed frames
      }
    }

    ws.onerror = () => {
      setStatus('error')
      setIsThinking(false)
    }

    ws.onclose = () => {
      setStatus('disconnected')
      setIsThinking(false)
      // Auto-reconnect after 3 seconds
      reconnectTimer.current = setTimeout(connect, 3000)
    }
  }, [userId, addMessage])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback(
    (text: string) => {
      if (!text.trim() || wsRef.current?.readyState !== WebSocket.OPEN) return

      addMessage('user', text.trim())
      setIsThinking(true)

      wsRef.current.send(
        JSON.stringify({ type: 'chat', message: text.trim(), session_id: '' })
      )
    },
    [addMessage]
  )

  const resetSession = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: 'reset' }))
    setMessages([])
  }, [])

  return { messages, status, isThinking, sendMessage, resetSession }
}

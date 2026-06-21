import { useEffect, useRef } from 'react'
import type { Message, ConnectionStatus } from '../hooks/useChat'
import { MessageBubble } from './MessageBubble'
import { ThinkingIndicator } from './ThinkingIndicator'
import { MessageInput } from './MessageInput'

interface Props {
  messages: Message[]
  status: ConnectionStatus
  isThinking: boolean
  userName: string
  onSend: (text: string) => void
  onReset: () => void
  onLogout: () => void
}

const STATUS_DOT: Record<ConnectionStatus, string> = {
  connecting:   'bg-yellow-400',
  connected:    'bg-green-400',
  disconnected: 'bg-red-400',
  error:        'bg-red-400',
}

export function ChatWindow({
  messages, status, isThinking, userName, onSend, onReset, onLogout,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🏠</span>
          <div>
            <h1 className="text-base font-semibold text-gray-800 leading-tight">AI Home Assistant</h1>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${STATUS_DOT[status]}`} />
              <span className="text-xs text-gray-500 capitalize">{status}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">👤 {userName}</span>
          <button
            onClick={onReset}
            className="text-xs text-gray-400 hover:text-gray-600 border border-gray-200 rounded-lg px-2.5 py-1 transition-colors"
            title="Clear conversation"
          >
            Clear
          </button>
          <button
            onClick={onLogout}
            className="text-xs text-gray-400 hover:text-gray-600 border border-gray-200 rounded-lg px-2.5 py-1 transition-colors"
          >
            Switch user
          </button>
        </div>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-400">
            <span className="text-5xl">💬</span>
            <p className="text-sm text-center max-w-xs">
              Ask me anything about your family schedule, grocery list, or household tasks.
            </p>
            <div className="flex flex-wrap gap-2 justify-center mt-2">
              {[
                'Add milk and eggs 🛒',
                "What's on this week? 📅",
                'Remind dad to mow the lawn ✅',
                "What's on the grocery list?",
              ].map(hint => (
                <button
                  key={hint}
                  onClick={() => onSend(hint)}
                  className="text-xs bg-white border border-gray-200 rounded-full px-3 py-1.5 text-gray-600 hover:bg-emerald-50 hover:border-emerald-300 transition-colors"
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} userName={userName} />
        ))}

        {isThinking && <ThinkingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <MessageInput
        onSend={onSend}
        disabled={status !== 'connected' || isThinking}
        status={status}
      />
    </div>
  )
}

import type { Message } from '../hooks/useChat'
import { AgentBadge } from './AgentBadge'

interface Props {
  message: Message
  userName: string
}

function formatTime(d: Date) {
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function MessageBubble({ message, userName }: Props) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end mb-2">
        <div className="max-w-[72%]">
          <div className="bg-emerald-500 text-white px-4 py-2.5 rounded-2xl rounded-tr-sm text-sm leading-relaxed shadow-sm">
            {message.text}
          </div>
          <div className="text-right text-xs text-gray-400 mt-1 pr-1">
            {userName} · {formatTime(message.timestamp)}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start mb-2">
      <div className="max-w-[72%]">
        {message.agent && (
          <div className="mb-1 ml-1">
            <AgentBadge agent={message.agent} />
          </div>
        )}
        <div className="bg-white text-gray-800 px-4 py-2.5 rounded-2xl rounded-tl-sm text-sm leading-relaxed shadow-sm whitespace-pre-wrap">
          {message.text}
        </div>
        <div className="text-xs text-gray-400 mt-1 ml-1">
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  )
}

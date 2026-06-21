import { useState } from 'react'
import type { ConnectionStatus } from '../hooks/useChat'

interface Props {
  onSend: (text: string) => void
  disabled: boolean
  status: ConnectionStatus
}

const STATUS_TEXT: Record<ConnectionStatus, string> = {
  connecting:   'Connecting to backend...',
  connected:    '',
  disconnected: 'Disconnected — retrying...',
  error:        'Connection error — retrying...',
}

const STATUS_COLOR: Record<ConnectionStatus, string> = {
  connecting:   'text-yellow-500',
  connected:    '',
  disconnected: 'text-red-500',
  error:        'text-red-500',
}

export function MessageInput({ onSend, disabled, status }: Props) {
  const [text, setText] = useState('')

  const submit = () => {
    if (!text.trim() || disabled) return
    onSend(text)
    setText('')
  }

  const statusMsg = STATUS_TEXT[status]

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      {statusMsg && (
        <p className={`text-xs mb-2 ${STATUS_COLOR[status]}`}>{statusMsg}</p>
      )}
      <div className="flex gap-2 items-end">
        <textarea
          rows={1}
          className="flex-1 border border-gray-300 rounded-xl px-4 py-2.5 text-sm text-gray-800 resize-none focus:outline-none focus:ring-2 focus:ring-emerald-400 max-h-32"
          placeholder="Try: add milk to the grocery list, or what's on this week?"
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          disabled={disabled}
        />
        <button
          onClick={submit}
          disabled={disabled || !text.trim()}
          className="bg-emerald-500 hover:bg-emerald-600 disabled:bg-gray-300 text-white rounded-xl px-4 py-2.5 text-sm font-medium transition-colors flex-shrink-0"
        >
          Send
        </button>
      </div>
    </div>
  )
}

import { useState } from 'react'

interface Props {
  onLogin: (name: string) => void
}

export function LoginScreen({ onLogin }: Props) {
  const [name, setName] = useState('')

  const submit = () => {
    const trimmed = name.trim()
    if (trimmed) onLogin(trimmed)
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-emerald-50 to-teal-100">
      <div className="bg-white rounded-2xl shadow-xl p-10 w-full max-w-sm flex flex-col gap-6">
        {/* Logo */}
        <div className="flex flex-col items-center gap-2">
          <div className="text-5xl">🏠</div>
          <h1 className="text-2xl font-bold text-gray-800">AI Home Assistant</h1>
          <p className="text-sm text-gray-500 text-center">
            Family coordination, powered by AI
          </p>
        </div>

        {/* Name input */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700">
            Who are you?
          </label>
          <input
            className="border border-gray-300 rounded-lg px-4 py-2.5 text-gray-800 focus:outline-none focus:ring-2 focus:ring-emerald-400"
            placeholder="e.g. mom, dad, Emma..."
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            autoFocus
          />
        </div>

        <button
          onClick={submit}
          disabled={!name.trim()}
          className="bg-emerald-500 hover:bg-emerald-600 disabled:bg-gray-300 text-white font-semibold py-2.5 rounded-lg transition-colors"
        >
          Start chatting
        </button>

        <p className="text-xs text-gray-400 text-center">
          Your name is used to attribute messages in the shared family data.
        </p>
      </div>
    </div>
  )
}

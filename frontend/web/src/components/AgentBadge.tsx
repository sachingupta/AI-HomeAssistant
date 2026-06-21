import type { AgentName } from '../hooks/useChat'

const AGENT_CONFIG: Record<AgentName, { label: string; color: string; emoji: string }> = {
  grocery:      { label: 'Grocery',      color: 'bg-green-100 text-green-700',   emoji: '🛒' },
  events:       { label: 'Events',       color: 'bg-blue-100 text-blue-700',     emoji: '📅' },
  todos:        { label: 'Todos',        color: 'bg-purple-100 text-purple-700', emoji: '✅' },
  orchestrator: { label: 'Assistant',    color: 'bg-gray-100 text-gray-600',     emoji: '🤖' },
  system:       { label: 'System',       color: 'bg-red-100 text-red-600',       emoji: '⚠️' },
}

export function AgentBadge({ agent }: { agent: AgentName }) {
  const cfg = AGENT_CONFIG[agent] ?? AGENT_CONFIG.orchestrator
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${cfg.color}`}>
      <span>{cfg.emoji}</span>
      {cfg.label}
    </span>
  )
}

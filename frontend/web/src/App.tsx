import { useState } from 'react'
import { LoginScreen } from './components/LoginScreen'
import { ChatWindow } from './components/ChatWindow'
import { useChat } from './hooks/useChat'

function ChatApp({ userName, onLogout }: { userName: string; onLogout: () => void }) {
  const { messages, status, isThinking, sendMessage, resetSession } = useChat(userName)
  return (
    <ChatWindow
      messages={messages}
      status={status}
      isThinking={isThinking}
      userName={userName}
      onSend={sendMessage}
      onReset={resetSession}
      onLogout={onLogout}
    />
  )
}

export default function App() {
  const [userName, setUserName] = useState<string | null>(
    () => sessionStorage.getItem('aiha_user')
  )

  const handleLogin = (name: string) => {
    sessionStorage.setItem('aiha_user', name)
    setUserName(name)
  }

  const handleLogout = () => {
    sessionStorage.removeItem('aiha_user')
    setUserName(null)
  }

  if (!userName) return <LoginScreen onLogin={handleLogin} />
  return <ChatApp userName={userName} onLogout={handleLogout} />
}

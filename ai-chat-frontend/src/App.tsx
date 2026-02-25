import { useState } from 'react'
import { cn } from '@/lib/utils'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import { useChat } from './hooks/useChat'
import { useTheme } from './hooks/useTheme'
import { getSessionHistory } from './api/chat'

export default function App() {
  const {
    sessions,
    activeSessionId,
    messages,
    status,
    loading,
    sendMessage,
    startNewChat,
    selectSession,
  } = useChat()

  const { theme, toggleTheme } = useTheme()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleSelectSession = async (id: string) => {
    try {
      const data = await getSessionHistory(id)
      selectSession(data.session_id, data.title, data.messages)
      setSidebarOpen(false)
    } catch {
      console.error('Failed to load session')
    }
  }

  const handleNewChat = () => {
    startNewChat()
    setSidebarOpen(false)
  }

  return (
    <div className="flex h-full overflow-hidden bg-[var(--app-bg)] text-[var(--app-text)] relative">

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden cursor-pointer"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={cn(
        'fixed inset-y-0 left-0 z-50 transition-transform duration-300 ease-in-out',
        'md:relative md:translate-x-0 md:z-auto',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelect={handleSelectSession}
          onNewChat={handleNewChat}
          theme={theme}
          toggleTheme={toggleTheme}
        />
      </div>

      {/* Main content */}
      <main className="flex-1 min-w-0 h-full">
        <ChatWindow
          messages={messages}
          status={status}
          loading={loading}
          onSend={sendMessage}
          onOpenSidebar={() => setSidebarOpen(true)}
        />
      </main>
    </div>
  )
}

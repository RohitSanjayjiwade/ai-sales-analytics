import { useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import type { Message } from '../types'

interface Props {
  messages: Message[]
  status: string | null
  loading: boolean
  onSend: (text: string) => void
  onOpenSidebar: () => void
}

const SUGGESTIONS = [
  { icon: '📈', text: "What is today's total sales?" },
  { icon: '🏆', text: 'Show top 5 selling products' },
  { icon: '📦', text: 'How many orders this week?' },
  { icon: '🗂️', text: 'Sales by category this month' },
]

export default function ChatWindow({ messages, status, loading, onSend, onOpenSidebar }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status])

  const isEmpty = messages.length === 0

  return (
    <div className="flex flex-col h-full bg-[var(--app-bg)]">

      {/* ── Mobile top bar (hidden on md+) ── */}
      <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-[var(--app-border)] shrink-0">
        <button
          onClick={onOpenSidebar}
          className="w-8 h-8 flex flex-col justify-center items-center gap-1.5 rounded-lg hover:bg-[var(--app-surface-hover)] transition-colors cursor-pointer"
          aria-label="Open sidebar"
        >
          <span className="w-5 h-px bg-[var(--app-text-muted)] block" />
          <span className="w-4 h-px bg-[var(--app-text-muted)] block" />
          <span className="w-5 h-px bg-[var(--app-text-muted)] block" />
        </button>
        <span className="text-sm font-medium text-[var(--app-text-muted)]">AI Analytics</span>
      </div>

      {/* ── Scrollable messages area ── */}
      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          /* Welcome / empty state */
          <div className="flex flex-col items-center justify-center min-h-full gap-6 px-4 py-10">
            <div className="text-center">
              <div className="w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-gradient-to-br from-teal-500 to-teal-800 flex items-center justify-center text-2xl md:text-3xl mx-auto mb-4 shadow-xl shadow-teal-900/40">
                📊
              </div>
              <h1 className="text-xl md:text-2xl font-semibold text-[var(--app-text)] mb-2 tracking-tight">
                AI Analytics Assistant
              </h1>
              <p className="text-sm text-[var(--app-text-muted)]">
                Ask questions about your business data
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-md">
              {SUGGESTIONS.map(({ icon, text }) => (
                <Button
                  key={text}
                  variant="outline"
                  onClick={() => onSend(text)}
                  className="h-auto py-3 px-4 border-[var(--app-border)] bg-[var(--app-sidebar)] hover:bg-[var(--app-input-bg)] hover:border-[var(--app-border-strong)] text-left flex items-start gap-2.5 rounded-xl transition-all duration-150 group cursor-pointer"
                >
                  <span className="text-base shrink-0 mt-px">{icon}</span>
                  <span className="text-[11px] text-[var(--app-text-muted)] group-hover:text-[var(--app-text)] leading-snug transition-colors">
                    {text}
                  </span>
                </Button>
              ))}
            </div>
          </div>
        ) : (
          /* Message list — stick to bottom */
          <div className="min-h-full flex flex-col justify-end">
            <div className="pt-4 pb-2 max-w-4xl mx-auto w-full">
              {messages.map((msg, idx) => {
                const prevMsg = messages[idx - 1]
                const isNewTurn = msg.role === 'user' && idx > 0 && prevMsg?.role === 'assistant'
                return (
                  <div key={msg.id} className={isNewTurn ? 'mt-6' : undefined}>
                    <MessageBubble message={msg} />
                  </div>
                )
              })}
            </div>

            {/* Bouncing dots status */}
            {status && (
              <div className="flex items-center gap-3 px-4 md:px-6 pb-3 max-w-4xl mx-auto w-full">
                <div className="flex gap-1 items-center">
                  {[0, 150, 300].map((delay) => (
                    <span
                      key={delay}
                      className="w-1.5 h-1.5 rounded-full bg-teal-500 inline-block animate-bounce"
                      style={{ animationDelay: `${delay}ms` }}
                    />
                  ))}
                </div>
                <span className="text-[11px] text-[var(--app-text-subtle)]">{status}</span>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* ── Input bar ── */}
      <div className="border-t border-[var(--app-border)] bg-[var(--app-bg)]">
        <div className="max-w-4xl mx-auto px-3 md:px-4 pb-4 pt-3">
          <ChatInput onSend={onSend} disabled={loading} />
        </div>
      </div>
    </div>
  )
}

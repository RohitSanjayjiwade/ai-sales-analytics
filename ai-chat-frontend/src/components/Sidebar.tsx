import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import type { Session } from '../types'

interface Props {
  sessions: Session[]
  activeSessionId?: string
  onSelect: (id: string) => void
  onNewChat: () => void
  theme: 'dark' | 'light'
  toggleTheme: () => void
}

function groupLabel(dateStr: string): string {
  const diff = Math.floor(
    (Date.now() - new Date(dateStr).getTime()) / 86_400_000
  )
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  if (diff < 7) return 'This Week'
  return 'Older'
}

const GROUP_ORDER = ['Today', 'Yesterday', 'This Week', 'Older']

export default function Sidebar({ sessions, activeSessionId, onSelect, onNewChat, theme, toggleTheme }: Props) {
  const grouped = sessions.reduce<Record<string, Session[]>>((acc, s) => {
    const g = groupLabel(s.created_at)
    ;(acc[g] ??= []).push(s)
    return acc
  }, {})

  return (
    <aside className="w-[260px] flex flex-col h-full bg-[var(--app-sidebar)] border-r border-[var(--app-border)] shrink-0">
      {/* Brand */}
      <div className="px-4 pt-5 pb-4 border-b border-[var(--app-border)]">
        <div className="flex items-center gap-2.5 mb-4">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center text-white text-xs font-bold shadow-lg shadow-teal-900/40">
            AI
          </div>
          <div>
            <p className="text-[13px] font-semibold text-[var(--app-text)] leading-none">Analytics</p>
            <p className="text-[10px] text-[var(--app-text-muted)] leading-none mt-0.5">Chat Assistant</p>
          </div>
        </div>
        <Button
          onClick={onNewChat}
          className="w-full h-9 text-sm bg-teal-600 hover:bg-teal-500 active:bg-teal-700 text-white font-medium rounded-xl transition-colors shadow-lg shadow-teal-900/30 cursor-pointer"
        >
          <span className="mr-1 text-base leading-none">+</span> New Chat
        </Button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto py-2 px-2">
        {sessions.length === 0 ? (
          <div className="text-center mt-10 px-4">
            <div className="text-3xl mb-2 opacity-30">💬</div>
            <p className="text-[11px] text-[var(--app-text-muted)] leading-relaxed">
              No conversations yet.<br />Start by asking a question.
            </p>
          </div>
        ) : (
          GROUP_ORDER.map((group) => {
            const items = grouped[group]
            if (!items?.length) return null
            return (
              <div key={group} className="mb-3">
                <p className="text-[10px] font-semibold text-[var(--app-text-faint)] uppercase tracking-widest px-3 py-1.5">
                  {group}
                </p>
                {items.map((s) => {
                  const isActive = s.id === activeSessionId
                  return (
                    <button
                      key={s.id}
                      onClick={() => onSelect(s.id)}
                      className={cn(
                        'w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-lg mb-0.5 text-xs transition-all duration-150 cursor-pointer',
                        isActive
                          ? 'bg-[var(--app-surface-hover)] text-[var(--app-text)] border-l-[2px] border-teal-500 pl-[10px]'
                          : 'text-[var(--app-text-muted)] hover:bg-[var(--app-surface-hover)] hover:text-[var(--app-text)]'
                      )}
                    >
                      <svg
                        className={cn('w-3.5 h-3.5 shrink-0', isActive ? 'text-teal-500' : 'text-[var(--app-text-faint)]')}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                          d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                        />
                      </svg>
                      <span className="truncate">{s.title || 'Untitled'}</span>
                    </button>
                  )
                })}
              </div>
            )
          })
        )}
      </div>

      {/* Footer — version + theme toggle */}
      <div className="px-4 py-3 border-t border-[var(--app-border)] flex items-center justify-between">
        <span className="text-[10px] text-[var(--app-text-faint)]">AI Chat Analytics</span>
        <button
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-[var(--app-surface-hover)] text-[var(--app-text-muted)] transition-colors cursor-pointer"
        >
          {theme === 'dark' ? (
            /* Sun */
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
              />
            </svg>
          ) : (
            /* Moon */
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
              />
            </svg>
          )}
        </button>
      </div>
    </aside>
  )
}

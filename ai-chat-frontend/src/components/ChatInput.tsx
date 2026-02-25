import { useState, useRef, useEffect } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

interface Props {
  onSend: (text: string) => void
  disabled: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 180) + 'px'
  }, [input])

  const handleSend = () => {
    const text = input.trim()
    if (!text || disabled) return
    onSend(text)
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const canSend = input.trim().length > 0 && !disabled

  return (
    <div>
      <div className={cn(
        'flex items-center gap-3 bg-[var(--app-input-bg)] border rounded-2xl px-4 py-2.5 transition-all duration-150',
        disabled
          ? 'border-[var(--app-border)]'
          : 'border-[var(--app-border-strong)] hover:border-[var(--app-text-faint)] focus-within:border-teal-600/60'
      )}>
        <Textarea
          ref={textareaRef}
          className="flex-1 resize-none bg-transparent border-0 shadow-none text-[var(--app-text)] placeholder:text-[var(--app-text-subtle)] text-sm leading-relaxed !min-h-[36px] max-h-[180px] focus-visible:ring-0 px-0 py-1 font-[inherit]"
          placeholder="Ask about your business data…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
        />

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={!canSend}
          className={cn(
            'w-8 h-8 rounded-xl flex items-center justify-center shrink-0 transition-all duration-150',
            canSend
              ? 'bg-teal-600 hover:bg-teal-500 active:scale-95 text-white shadow-md shadow-teal-900/50 cursor-pointer'
              : 'bg-[var(--app-surface-hover)] text-[var(--app-text-faint)] cursor-not-allowed'
          )}
        >
          {disabled
            ? (
              /* Spinner */
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
            )
            : (
              /* Arrow */
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            )
          }
        </button>
      </div>

      <p className="text-[10px] text-[var(--app-text-subtle)] text-center mt-2 select-none">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  )
}

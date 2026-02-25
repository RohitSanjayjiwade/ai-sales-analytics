import { useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import type { Message } from '../types'

// ── SQL syntax highlighter ─────────────────────────────────────────────────
const SQL_KEYWORDS = new Set([
  'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'JOIN', 'LEFT', 'RIGHT',
  'INNER', 'OUTER', 'CROSS', 'ON', 'GROUP', 'ORDER', 'BY', 'HAVING', 'LIMIT',
  'OFFSET', 'AS', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'BETWEEN',
  'LIKE', 'IS', 'NULL', 'WITH', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'UNION',
  'ALL', 'COALESCE', 'CAST', 'OVER', 'PARTITION', 'SET', 'DATETIME', 'STRFTIME',
  'DATE', 'TIME', 'JULIANDAY', 'ISNULL', 'IFNULL', 'INTO', 'VALUES',
])

const TOKEN_RE = /('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b|\s+|[^\w\s])/g

function SQLHighlight({ sql }: { sql: string }) {
  const tokens = sql.match(TOKEN_RE) ?? [sql]
  return (
    <>
      {tokens.map((tok, i) => {
        if (/^['"]/.test(tok))
          return <span key={i} className="text-amber-600 dark:text-amber-300">{tok}</span>
        if (/^\d/.test(tok) && tok.trim())
          return <span key={i} className="text-sky-600 dark:text-sky-400">{tok}</span>
        if (SQL_KEYWORDS.has(tok.toUpperCase()))
          return <span key={i} className="text-violet-600 dark:text-violet-400 font-semibold">{tok}</span>
        if (/^[A-Za-z_]/.test(tok))
          return <span key={i} className="text-teal-700 dark:text-teal-300">{tok}</span>
        if (/\S/.test(tok))
          return <span key={i} className="text-slate-500 dark:text-slate-400">{tok}</span>
        return <span key={i}>{tok}</span>
      })}
    </>
  )
}

// ── Inline markdown (bold, italic, inline code) ────────────────────────────
function formatInline(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g)
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith('**') && p.endsWith('**'))
          return <strong key={i} className="font-semibold text-[var(--app-text)]">{p.slice(2, -2)}</strong>
        if (p.startsWith('*') && p.endsWith('*'))
          return <em key={i} className="italic">{p.slice(1, -1)}</em>
        if (p.startsWith('`') && p.endsWith('`'))
          return (
            <code key={i} className="bg-[var(--app-border-strong)] px-1.5 py-0.5 rounded text-[11px] font-mono text-teal-700 dark:text-teal-300">
              {p.slice(1, -1)}
            </code>
          )
        return <span key={i}>{p}</span>
      })}
    </>
  )
}

// ── Block markdown renderer ─────────────────────────────────────────────────
function formatMessage(text: string): ReactNode {
  const blocks = text.split(/\n{2,}/)
  return (
    <div className="space-y-2">
      {blocks.map((block, bi) => {
        const lines = block.split('\n')
        const bulletLines = lines.filter((l) => /^[-*]\s+/.test(l.trim()))
        const numberedLines = lines.filter((l) => /^\d+\.\s+/.test(l.trim()))

        if (bulletLines.length > 0 && bulletLines.length === lines.filter((l) => l.trim()).length) {
          return (
            <ul key={bi} className="ml-4 space-y-0.5 list-disc">
              {bulletLines.map((l, li) => (
                <li key={li} className="text-sm text-[var(--app-text)]">
                  {formatInline(l.trim().replace(/^[-*]\s+/, ''))}
                </li>
              ))}
            </ul>
          )
        }

        if (numberedLines.length > 0 && numberedLines.length === lines.filter((l) => l.trim()).length) {
          return (
            <ol key={bi} className="ml-4 space-y-0.5 list-decimal">
              {numberedLines.map((l, li) => (
                <li key={li} className="text-sm text-[var(--app-text)]">
                  {formatInline(l.trim().replace(/^\d+\.\s+/, ''))}
                </li>
              ))}
            </ol>
          )
        }

        return (
          <p key={bi} className="text-sm leading-relaxed text-[var(--app-text)]">
            {formatInline(block.replace(/\n/g, ' '))}
          </p>
        )
      })}
    </div>
  )
}

// ── Component ───────────────────────────────────────────────────────────────
interface Props { message: Message }

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'
  const isFailed = message.status === 'failed'
  const [sqlOpen, setSqlOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  const copySQL = () => {
    if (!message.sql) return
    navigator.clipboard.writeText(message.sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn('flex gap-2 md:gap-3 px-3 md:px-6 py-2.5', isUser && 'flex-row-reverse')}>
      {/* Avatar */}
      <div className={cn(
        'w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 mt-1 select-none',
        isUser
          ? 'bg-teal-600 text-white shadow-md shadow-teal-900/50'
          : 'bg-[var(--app-surface-hover)] text-teal-600 dark:text-teal-400 border border-[var(--app-border-strong)]'
      )}>
        {isUser ? 'You' : 'AI'}
      </div>

      {/* Content column */}
      <div className={cn('flex flex-col gap-2', isUser ? 'items-end max-w-[72%]' : 'flex-1 min-w-0')}>

        {/* SQL thinking panel (assistant only) */}
        {!isUser && message.sql && (
          <div className="w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-sql-header)] overflow-hidden">
            {/* Header */}
            <button
              onClick={() => setSqlOpen((o) => !o)}
              className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-[var(--app-surface-hover)] transition-colors group cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <svg
                  className={cn(
                    'w-3.5 h-3.5 text-[var(--app-text-subtle)] transition-transform duration-200',
                    sqlOpen && 'rotate-90'
                  )}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                <span className="text-[11px] text-[var(--app-text-muted)] group-hover:text-[var(--app-text)] transition-colors">
                  Query executed
                </span>
              </div>
              <span className="text-[10px] font-mono text-[var(--app-text-subtle)] bg-[var(--app-input-bg)] border border-[var(--app-border-strong)] px-1.5 py-0.5 rounded">
                SQL
              </span>
            </button>

            {/* Body (animated) */}
            <div className={cn('sql-collapsible', sqlOpen && 'open')}>
              <div>
                <div className="border-t border-[var(--app-border)] bg-[var(--app-sql-body)] relative">
                  {/* Copy button */}
                  <button
                    onClick={copySQL}
                    className="absolute top-2.5 right-3 text-[10px] text-[var(--app-text-faint)] hover:text-[var(--app-text-muted)] bg-[var(--app-input-bg)] border border-[var(--app-border)] px-2 py-0.5 rounded transition-colors cursor-pointer"
                  >
                    {copied ? '✓ copied' : 'copy'}
                  </button>
                  <pre className="px-4 py-3 text-[12px] leading-relaxed font-mono overflow-x-auto">
                    <SQLHighlight sql={message.sql} />
                  </pre>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Message bubble */}
        <div className={cn(
          'rounded-2xl px-4 py-3 text-sm',
          isUser
            ? 'bg-teal-700 text-white rounded-tr-sm shadow-md shadow-teal-900/40'
            : isFailed
            ? 'bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-300 border border-red-200 dark:border-red-900/40 rounded-tl-sm'
            : 'bg-[var(--app-surface)] border border-[var(--app-border)] rounded-tl-sm'
        )}>
          {message.content
            ? isUser
              ? <p className="text-sm leading-relaxed">{message.content}</p>
              : formatMessage(message.content)
            : <span className="cursor-blink text-[var(--app-text-subtle)] text-base">▌</span>
          }
        </div>
      </div>
    </div>
  )
}

import { useState, useRef, useCallback } from 'react'
import { sendMessageStream } from '../api/chat'
import type { Message, Session, StreamEvent } from '../types'

const generateId = () => Math.random().toString(36).slice(2)

export function useChat() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>()
  const [messages, setMessages] = useState<Message[]>([])
  const [status, setStatus] = useState<string | null>(null)  // "Analyzing..." etc
  const [loading, setLoading] = useState(false)
  const abortRef = useRef<(() => void) | null>(null)

  const selectSession = useCallback((sessionId: string, title: string, msgs: Message[]) => {
    setActiveSessionId(sessionId)
    setMessages(msgs)
    // ensure session is in list
    setSessions((prev) =>
      prev.find((s) => s.id === sessionId)
        ? prev
        : [{ id: sessionId, title, created_at: new Date().toISOString() }, ...prev]
    )
  }, [])

  const sendMessage = useCallback((text: string) => {
    if (!text.trim() || loading) return

    const userMsg: Message = { id: generateId(), role: 'user', content: text }
    const assistantMsg: Message = { id: generateId(), role: 'assistant', content: '' }

    setMessages((prev) => [...prev, userMsg, assistantMsg])
    setLoading(true)
    setStatus(null)

    const abort = sendMessageStream(
      text,
      activeSessionId,
      // onEvent
      (event: StreamEvent) => {
        if (event.type === 'status') {
          setStatus(event.message)
        }

        if (event.type === 'chunk') {
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            updated[updated.length - 1] = { ...last, content: last.content + event.content }
            return updated
          })
        }

        if (event.type === 'done') {
          setActiveSessionId(event.session_id)

          // Add to sessions list if new session
          setSessions((prev) => {
            const exists = prev.find((s) => s.id === event.session_id)
            if (exists) return prev
            return [
              { id: event.session_id, title: text.slice(0, 50), created_at: new Date().toISOString() },
              ...prev,
            ]
          })
        }

        if (event.type === 'sql') {
          setMessages((prev) => {
            const updated = [...prev]
            updated[updated.length - 1] = { ...updated[updated.length - 1], sql: event.query }
            return updated
          })
        }

        if (event.type === 'error') {
          setMessages((prev) => {
            const updated = [...prev]
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: event.message,
              status: 'failed',
            }
            return updated
          })
        }
      },
      // onDone
      () => {
        setLoading(false)
        setStatus(null)
      },
      // onError
      (err) => {
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: err,
            status: 'failed',
          }
          return updated
        })
        setLoading(false)
        setStatus(null)
      }
    )

    abortRef.current = abort
  }, [activeSessionId, loading])

  const startNewChat = useCallback(() => {
    if (abortRef.current) abortRef.current()
    setActiveSessionId(undefined)
    setMessages([])
    setStatus(null)
    setLoading(false)
  }, [])

  return {
    sessions,
    activeSessionId,
    messages,
    status,
    loading,
    sendMessage,
    startNewChat,
    selectSession,
  }
}

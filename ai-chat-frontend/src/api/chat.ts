import axios from 'axios'
import type { Message, StreamEvent } from '../types'

const BASE_URL = `${import.meta.env.VITE_API_BASE_URL ?? ''}/api/chat`

// ── Standard (non-streaming) ───────────────────────────────────────────────
export const sendMessage = async (message: string, sessionId?: string) => {
  const res = await axios.post(`${BASE_URL}/message/`, {
    message,
    session_id: sessionId,
  })
  return res.data as {
    session_id: string
    response: string
    metadata: { row_count: number; success: boolean }
  }
}

// ── Session history ────────────────────────────────────────────────────────
export const getSessionHistory = async (sessionId: string) => {
  const res = await axios.get(`${BASE_URL}/session/${sessionId}/`)
  return res.data as { session_id: string; title: string; messages: Message[] }
}

// ── Streaming (SSE) ────────────────────────────────────────────────────────
export const sendMessageStream = (
  message: string,
  sessionId: string | undefined,
  onEvent: (event: StreamEvent) => void,
  onDone: () => void,
  onError: (err: string) => void,
) => {
  const controller = new AbortController()

  fetch(`${BASE_URL}/message/stream/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        onError(`Server error: ${res.status}`)
        onDone()
        return
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()

      // Buffer handles the case where a network chunk splits an SSE event
      // mid-line — we keep the incomplete portion and prepend it to the next chunk.
      let buffer = ''
      let completed = false

      try {
        while (true) {
          const { done, value } = await reader.read()

          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // Split on newlines but keep the last (possibly incomplete) line in buffer
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const event: StreamEvent = JSON.parse(line.slice(6))
              onEvent(event)

              if (event.type === 'done') {
                completed = true
                onDone()
                return   // stop reading — stream is finished
              }

              if (event.type === 'error') {
                completed = true
                onError(event.message)
                onDone()
                return
              }
            } catch {
              // skip malformed line
            }
          }
        }
      } finally {
        // If stream closed unexpectedly (network drop, server timeout)
        // without sending a done/error event — unblock the UI.
        if (!completed) onDone()
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError('Connection failed. Please try again.')
        onDone()
      }
    })

  return () => controller.abort()
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  status?: 'success' | 'failed'
  created_at?: string
  sql?: string
}

export interface Session {
  id: string
  title: string
  created_at: string
}

export type StreamEvent =
  | { type: 'status'; message: string }
  | { type: 'chunk'; content: string }
  | { type: 'done'; session_id: string; row_count: number }
  | { type: 'error'; message: string }
  | { type: 'sql'; query: string }

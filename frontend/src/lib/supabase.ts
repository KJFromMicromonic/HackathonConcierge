import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://eefdoafrhcehtafkewnc.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVlZmRvYWZyaGNlaHRhZmtld25jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE4MTEyNjAsImV4cCI6MjA4NzM4NzI2MH0.lVoKaUFkPEEoGquNiyEjdlUoK9RmT2Qv2tB3FnwNnas'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// API base URL
export const API_BASE = import.meta.env.DEV ? 'http://localhost:8000' : ''

// Helper for authenticated API calls
export async function apiCall(endpoint: string, options: RequestInit = {}) {
  const { data: { session } } = await supabase.auth.getSession()

  if (!session?.access_token) {
    throw new Error('Not authenticated')
  }

  return fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${session.access_token}`,
    },
  })
}

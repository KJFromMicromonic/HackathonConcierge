import { useState, useEffect } from 'react'
import { apiCall } from '../lib/supabase'

interface Memory {
  memory_id: string
  content: string
  metadata?: Record<string, unknown>
  created_at?: string
}

interface MemoriesListProps {
  isCollapsed: boolean
}

export function MemoriesList({ isCollapsed }: MemoriesListProps) {
  const [memories, setMemories] = useState<Memory[]>([])
  const [loading, setLoading] = useState(true)

  const fetchMemories = async () => {
    try {
      const res = await apiCall('/me/memories')
      const data = await res.json()
      setMemories(data.memories || [])
    } catch (error) {
      console.error('Failed to fetch memories:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMemories()
  }, [])

  const deleteMemory = async (memoryId: string) => {
    try {
      await apiCall(`/me/memories/${memoryId}`, {
        method: 'DELETE',
      })
      fetchMemories()
    } catch (error) {
      console.error('Failed to delete memory:', error)
    }
  }

  if (isCollapsed) {
    return (
      <div className="sidebar-section collapsed">
        <div className="section-icon" title="Memories">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
        </div>
      </div>
    )
  }

  return (
    <div className="sidebar-section memories-section">
      <div className="section-header">
        <h3>Memories</h3>
        <span className="section-count">{memories.length}</span>
      </div>

      <div className="section-content">
        {loading ? (
          <div className="section-loading">Loading...</div>
        ) : memories.length === 0 ? (
          <div className="section-empty">No memories yet</div>
        ) : (
          <ul className="memories-list">
            {memories.map((mem, i) => (
              <li key={mem.memory_id || i} className="memory-item">
                <span className="memory-content">{mem.content}</span>
                <button
                  className="delete-memory-btn"
                  onClick={() => deleteMemory(mem.memory_id)}
                  title="Delete memory"
                >
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

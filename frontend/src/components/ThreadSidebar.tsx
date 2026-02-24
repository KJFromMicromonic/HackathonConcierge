import { useEffect, useState } from 'react';
import { apiCall } from '../lib/supabase';
import { DocumentsList } from './DocumentsList';
import { MemoriesList } from './MemoriesList';

interface Thread {
  thread_id: string;
  created_at: string;
  message_count: number;
  preview: string;
}

interface ThreadSidebarProps {
  currentThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onNewThread: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const ThreadSidebar = ({
  currentThreadId,
  onSelectThread,
  onNewThread,
  isCollapsed,
  onToggleCollapse
}: ThreadSidebarProps) => {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchThreads = async () => {
    try {
      const response = await apiCall('/threads');
      const data = await response.json();
      setThreads(data.threads || []);
    } catch (error) {
      console.error('Failed to fetch threads:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchThreads();
  }, []);

  // Refresh when a new thread is created
  useEffect(() => {
    if (currentThreadId) {
      fetchThreads();
    }
  }, [currentThreadId]);

  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className={`thread-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      {/* Collapse toggle button */}
      <button
        className="sidebar-collapse-btn"
        onClick={onToggleCollapse}
        aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
          {isCollapsed ? (
            <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
          ) : (
            <path d="M15.41 16.59L10.83 12l4.58-4.59L14 6l-6 6 6 6 1.41-1.41z"/>
          )}
        </svg>
      </button>

      <div className="sidebar-header">
        <h2>{isCollapsed ? '' : 'Threads'}</h2>
        <button
          className="new-thread-btn"
          onClick={onNewThread}
          title="New conversation"
        >
          {isCollapsed ? '+' : '+ New'}
        </button>
      </div>

      <div className="thread-list">
        {loading ? (
          <div className="loading-threads">{isCollapsed ? '...' : 'Loading...'}</div>
        ) : threads.length === 0 ? (
          <div className="empty-threads">
            {!isCollapsed && (
              <>
                <p>No conversations yet</p>
                <p className="hint">Start chatting to create one!</p>
              </>
            )}
          </div>
        ) : (
          threads.map((thread) => (
            <div
              key={thread.thread_id}
              className={`thread-item ${thread.thread_id === currentThreadId ? 'active' : ''}`}
              onClick={() => onSelectThread(thread.thread_id)}
              title={isCollapsed ? thread.preview : undefined}
            >
              {isCollapsed ? (
                <div className="thread-icon">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
                  </svg>
                </div>
              ) : (
                <>
                  <div className="thread-preview">{thread.preview}</div>
                  <div className="thread-meta">
                    <span className="thread-date">{formatDate(thread.created_at)}</span>
                    <span className="message-count">{thread.message_count} msgs</span>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>

      {/* Documents Section */}
      <DocumentsList isCollapsed={isCollapsed} />

      {/* Memories Section */}
      <MemoriesList isCollapsed={isCollapsed} />
    </div>
  );
};

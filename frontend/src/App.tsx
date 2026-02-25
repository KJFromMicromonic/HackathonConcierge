import { useState, useEffect, useCallback, useRef } from 'react';
import { ThreadSidebar } from './components/ThreadSidebar';
import { ConversationHistory } from './components/ConversationHistory';
import { ChatInput } from './components/ChatInput';
import { VoiceInterface } from './components/VoiceInterface';
import { ModeToggle } from './components/ModeToggle';
import { ModelSelector } from './components/ModelSelector';
import { AuthForm } from './components/AuthForm';
import { useWebSocket } from './hooks/useWebSocket';
import { useAuth } from './contexts/AuthContext';
import { apiCall } from './lib/supabase';
import './styles/main.css';

type Mode = 'chat' | 'voice';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'notification';
  content: string;
  timestamp: Date;
  notificationType?: 'announcement' | 'activity' | 'team_activity';
}

function App() {
  const { user, profile, loading, signOut } = useAuth();

  // UI State
  const [mode, setMode] = useState<Mode>('chat');
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 768);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const stored = localStorage.getItem('aura_sidebar_collapsed');
    return stored === 'true';
  });
  const [selectedModelId, setSelectedModelId] = useState(() => {
    return localStorage.getItem('aura_chat_model') || 'claude-sonnet';
  });

  // Persist sidebar collapsed state
  const toggleSidebarCollapse = useCallback(() => {
    setSidebarCollapsed(prev => {
      const newValue = !prev;
      localStorage.setItem('aura_sidebar_collapsed', String(newValue));
      return newValue;
    });
  }, []);

  // Track processed responses to prevent duplicates
  const lastProcessedResponse = useRef<string>('');

  // WebSocket connection for chat mode
  const {
    isConnected,
    status,
    sendText,
    lastResponse,
    lastNotification,
    switchThread,
    createNewThread,
    isStreaming,
    streamingContent,
  } = useWebSocket(!!user);

  // Add user message to UI
  const addUserMessage = useCallback((content: string) => {
    const newMsg: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMsg]);
  }, []);

  // Handle assistant response (with deduplication)
  useEffect(() => {
    if (lastResponse && lastResponse !== lastProcessedResponse.current) {
      lastProcessedResponse.current = lastResponse;
      const newMsg: Message = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: lastResponse,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, newMsg]);
    }
  }, [lastResponse]);

  // Handle proactive notifications from activity feed
  const lastProcessedNotification = useRef<string>('');
  useEffect(() => {
    if (lastNotification && lastNotification.message !== lastProcessedNotification.current) {
      lastProcessedNotification.current = lastNotification.message;
      const notifMsg: Message = {
        id: `notif_${Date.now()}`,
        role: 'notification',
        content: lastNotification.message,
        timestamp: new Date(),
        notificationType: lastNotification.notification_type,
      };
      setMessages(prev => [...prev, notifMsg]);
    }
  }, [lastNotification]);

  // Handle thread selection
  const handleSelectThread = async (threadId: string) => {
    setCurrentThreadId(threadId);
    switchThread(threadId);

    // Load thread messages
    try {
      const response = await apiCall(`/threads/${threadId}`);
      const data = await response.json();

      setMessages(data.messages.map((m: any) => ({
        id: m.message_id,
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at)
      })));
      lastProcessedResponse.current = '';
    } catch (error) {
      console.error('Failed to load thread:', error);
    }

    if (window.innerWidth <= 768) {
      setSidebarOpen(false);
    }
  };

  // Handle new thread
  const handleNewThread = async () => {
    const threadId = await createNewThread();
    if (threadId) {
      setCurrentThreadId(threadId);
      setMessages([]);
      lastProcessedResponse.current = '';
    }

    if (window.innerWidth <= 768) {
      setSidebarOpen(false);
    }
  };

  // Handle model change
  const handleModelChange = useCallback((modelId: string) => {
    setSelectedModelId(modelId);
    localStorage.setItem('aura_chat_model', modelId);
  }, []);

  // Handle text send (chat mode)
  const handleSendText = (text: string) => {
    addUserMessage(text);
    sendText(text, selectedModelId);
  };

  // Handle voice transcripts — add to message history
  const handleUserTranscript = useCallback((text: string) => {
    addUserMessage(text);
  }, [addUserMessage]);

  const handleAgentResponse = useCallback((text: string) => {
    const newMsg: Message = {
      id: `assistant_voice_${Date.now()}`,
      role: 'assistant',
      content: text,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMsg]);
  }, []);

  // Responsive sidebar
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 768) {
        setSidebarOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isProcessing = status === 'thinking' || isStreaming;

  // Compute messages to display, including streaming message if active
  const displayMessages: Message[] = isStreaming
    ? [
        ...messages,
        {
          id: 'streaming',
          role: 'assistant' as const,
          content: streamingContent,
          timestamp: new Date()
        }
      ]
    : messages;

  // Show loading state
  if (loading) {
    return (
      <div className="auth-loading">
        <div className="auth-loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  // Show auth form if not logged in
  if (!user) {
    return <AuthForm />;
  }

  return (
    <div className={`app-container ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'} ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''} ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <ThreadSidebar
          currentThreadId={currentThreadId}
          onSelectThread={handleSelectThread}
          onNewThread={handleNewThread}
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={toggleSidebarCollapse}
        />
      </aside>

      {/* Sidebar overlay for mobile */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <main className="main-content">
        {/* Header */}
        <header className="app-header">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle sidebar"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
              <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
            </svg>
          </button>

          <h1 className="logo">
            <span className="logo-text">AURA</span>
            <span className="logo-tagline">Voice AI Concierge</span>
          </h1>

          <div className="header-right">
            <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
              <span className="status-dot"></span>
              <span className="status-text">
                {isConnected ? 'Connected' : 'Connecting...'}
              </span>
            </div>

            <button
              className="sign-out-btn"
              onClick={signOut}
              title={`Sign out (${user.email})`}
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/>
              </svg>
            </button>
          </div>
        </header>

        {/* Conversation */}
        <div className="conversation-container">
          <ConversationHistory
            messages={displayMessages}
            isVoiceMode={mode === 'voice'}
            userName={profile?.first_name}
          />
        </div>

        {/* Input Area */}
        <div className="input-area">
          <div className="input-controls">
            <ModeToggle
              mode={mode}
              onModeChange={setMode}
              disabled={isProcessing}
            />
            {mode === 'chat' && (
              <ModelSelector
                selectedModelId={selectedModelId}
                onModelChange={handleModelChange}
              />
            )}
          </div>

          {mode === 'chat' ? (
            <ChatInput
              onSendMessage={handleSendText}
              disabled={!isConnected || isProcessing}
              placeholder="Ask about Backboard, Speechmatics, or building voice AI..."
            />
          ) : (
            <VoiceInterface
              onSwitchToChat={() => setMode('chat')}
              onUserTranscript={handleUserTranscript}
              onAgentResponse={handleAgentResponse}
            />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;

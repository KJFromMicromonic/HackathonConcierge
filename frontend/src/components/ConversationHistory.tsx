import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ProvisioningStatus } from '../hooks/useWebSocket'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'notification'
  content: string
  timestamp: Date
  notificationType?: 'announcement' | 'activity' | 'team_activity'
}

interface ConversationHistoryProps {
  messages: Message[]
  interimTranscript?: string
  isVoiceMode?: boolean
  userName?: string | null
  provisioningStatus?: ProvisioningStatus | null
}

function ProvisioningCard({ status }: { status: ProvisioningStatus }) {
  const isUploading = status.step === 'uploading_docs'
  const isVerifying = status.step === 'verifying'
  const isComplete = status.step === 'complete'
  const showProgress = (isUploading || isVerifying) && status.total > 0
  const pct = showProgress ? Math.round((status.progress / status.total) * 100) : 0

  return (
    <div className="provisioning-card">
      <div className="provisioning-icon">
        {isComplete ? (
          <svg viewBox="0 0 24 24" width="32" height="32" fill="var(--lime)">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
        ) : (
          <div className="provisioning-spinner" />
        )}
      </div>
      <p className="provisioning-message">{status.message}</p>
      {showProgress && (
        <div className="provisioning-progress">
          <div className="provisioning-progress-bar" style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  )
}

export function ConversationHistory({
  messages,
  interimTranscript = '',
  isVoiceMode = false,
  userName,
  provisioningStatus,
}: ConversationHistoryProps) {
  return (
    <div className="conversation-history">
      {provisioningStatus ? (
        <div className="empty-state">
          <div className="aura-greeting">
            <h2>Setting up AURA</h2>
            <p>Preparing your personal AI assistant...</p>
            <ProvisioningCard status={provisioningStatus} />
          </div>
        </div>
      ) : messages.length === 0 ? (
        <div className="empty-state">
          <div className="aura-greeting">
            <h2>{userName ? `Hi ${userName}, I'm AURA` : `Hi, I'm AURA`}</h2>
            <p>Your AI concierge for Activate Your Voice</p>
            <div className="suggestions">
              <p>Try asking me:</p>
              <ul>
                <li>"What workshops are happening today?"</li>
                <li>"Tell me about the Persistent Memory track"</li>
                <li>"Where can I find the Speechmatics booth?"</li>
                <li>"What are the judging criteria?"</li>
              </ul>
            </div>
          </div>
        </div>
      ) : (
        <div className="messages">
          {messages.map((message) => (
            <div key={message.id} className={`message ${message.role} ${message.notificationType || ''}`}>
              <div className="message-avatar">
                {message.role === 'user' ? '👤' : message.role === 'notification' ? '📢' : '🤖'}
              </div>
              <div className="message-content">
                {message.role === 'notification' && (
                  <span className={`notification-badge ${message.notificationType || ''}`}>
                    {message.notificationType === 'announcement' ? 'Announcement'
                      : message.notificationType === 'team_activity' ? 'Team'
                      : 'Update'}
                  </span>
                )}
                <div className="message-text">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                </div>
                <span className="message-time">
                  {message.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              </div>
            </div>
          ))}

          {/* Interim transcript (voice mode only) */}
          {isVoiceMode && interimTranscript && (
            <div className="message user interim">
              <div className="message-avatar">👤</div>
              <div className="message-content">
                <p className="typing">{interimTranscript}...</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

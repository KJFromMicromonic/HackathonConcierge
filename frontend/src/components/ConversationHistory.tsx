import ReactMarkdown from 'react-markdown'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface ConversationHistoryProps {
  messages: Message[]
  interimTranscript?: string
  isVoiceMode?: boolean
  userName?: string | null
}

export function ConversationHistory({
  messages,
  interimTranscript = '',
  isVoiceMode = false,
  userName,
}: ConversationHistoryProps) {
  return (
    <div className="conversation-history">
      {messages.length === 0 ? (
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
            <div key={message.id} className={`message ${message.role}`}>
              <div className="message-avatar">
                {message.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content">
                <div className="message-text">
                  <ReactMarkdown>{message.content}</ReactMarkdown>
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

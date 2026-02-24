import { useEffect } from 'react'
import { useLiveKit } from '../hooks/useLiveKit'

interface VoiceInterfaceProps {
  onSwitchToChat: () => void
  onUserTranscript: (text: string) => void
  onAgentResponse: (text: string) => void
}

export function VoiceInterface({
  onSwitchToChat,
  onUserTranscript,
  onAgentResponse,
}: VoiceInterfaceProps) {
  const {
    isConnected,
    agentState,
    connect,
    disconnect,
    setMicEnabled,
    isMicEnabled,
    lastUserTranscript,
    lastAgentTranscript,
    interimUserTranscript,
    error,
  } = useLiveKit()

  // Forward transcripts to parent
  useEffect(() => {
    if (lastUserTranscript) {
      onUserTranscript(lastUserTranscript)
    }
  }, [lastUserTranscript, onUserTranscript])

  useEffect(() => {
    if (lastAgentTranscript) {
      onAgentResponse(lastAgentTranscript)
    }
  }, [lastAgentTranscript, onAgentResponse])

  const handleStartVoice = () => {
    connect()
  }

  const handleStopVoice = () => {
    disconnect()
    onSwitchToChat()
  }

  const handleToggleMute = () => {
    setMicEnabled(!isMicEnabled)
  }

  const getStatusText = () => {
    if (!isConnected) {
      if (agentState === 'connecting') return 'Connecting...'
      return 'Click to start voice conversation'
    }
    if (!isMicEnabled) return 'Microphone muted'

    switch (agentState) {
      case 'listening': return 'Listening...'
      case 'thinking': return 'Thinking...'
      case 'speaking': return 'Speaking...'
      default: return 'Connected'
    }
  }

  const isProcessing = agentState === 'thinking' || agentState === 'speaking'

  return (
    <div className="voice-interface">
      {!isConnected && agentState !== 'connecting' ? (
        // Inactive state - show start button
        <>
          <div className="status-display">
            <div className="status-indicator idle" />
            <span className="status-text">{getStatusText()}</span>
          </div>

          {error && (
            <div className="voice-error">
              <span>{error}</span>
            </div>
          )}

          <div className="orb-container">
            <button
              className="voice-orb"
              onClick={handleStartVoice}
            >
              <div className="orb-inner">
                <svg viewBox="0 0 24 24" className="mic-icon">
                  <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" fill="none" stroke="currentColor" strokeWidth="1.5"/>
                  <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" fill="none" stroke="currentColor" strokeWidth="1.5"/>
                </svg>
              </div>
            </button>
            <p className="orb-hint">Tap to start conversation</p>
          </div>
        </>
      ) : (
        // Active / connecting state - show controls
        <>
          <div className="status-display">
            <div className={`status-indicator ${!isMicEnabled ? 'muted' : agentState}`} />
            <span className="status-text">{getStatusText()}</span>
          </div>

          {interimUserTranscript && (
            <div className="interim-transcript">
              <span>{interimUserTranscript}...</span>
            </div>
          )}

          <div className="orb-container">
            <button
              className={`voice-orb active ${isProcessing ? 'processing' : ''} ${!isMicEnabled ? 'muted' : ''}`}
              onClick={handleStopVoice}
            >
              <div className="orb-inner">
                <svg viewBox="0 0 24 24" className="mic-icon active">
                  <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                  <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                </svg>
              </div>
            </button>
            <p className="orb-hint">Tap to end conversation</p>
          </div>

          {/* Voice visualizer */}
          <div className="voice-visualizer">
            <div className={`voice-wave ${isMicEnabled && (agentState === 'listening') ? 'listening' : ''}`}>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>

          {/* Voice controls */}
          <div className="voice-controls">
            <button
              className={`voice-control-btn mute-btn ${!isMicEnabled ? 'active' : ''}`}
              onClick={handleToggleMute}
              title={isMicEnabled ? 'Mute' : 'Unmute'}
              disabled={!isConnected}
            >
              {!isMicEnabled ? (
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                  <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                  <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5z"/>
                  <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                </svg>
              )}
              <span>{isMicEnabled ? 'Mute' : 'Unmute'}</span>
            </button>

            <button
              className="voice-control-btn end-btn"
              onClick={handleStopVoice}
              title="End Voice Mode"
            >
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z"/>
              </svg>
              <span>End</span>
            </button>
          </div>
        </>
      )}
    </div>
  )
}

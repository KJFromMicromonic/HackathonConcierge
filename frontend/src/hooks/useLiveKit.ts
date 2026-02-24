import { useState, useRef, useCallback, useEffect } from 'react'
import {
  Room,
  RoomEvent,
  Track,
  RemoteTrack,
  TranscriptionSegment,
  Participant,
} from 'livekit-client'
import { apiCall } from '../lib/supabase'

type AgentState = 'disconnected' | 'connecting' | 'listening' | 'thinking' | 'speaking'

interface UseLiveKitReturn {
  isConnected: boolean
  agentState: AgentState
  connect: () => Promise<void>
  disconnect: () => void
  setMicEnabled: (enabled: boolean) => void
  isMicEnabled: boolean
  isAgentSpeaking: boolean
  lastUserTranscript: string | null
  lastAgentTranscript: string | null
  interimUserTranscript: string
  error: string | null
}

export function useLiveKit(): UseLiveKitReturn {
  const [isConnected, setIsConnected] = useState(false)
  const [agentState, setAgentState] = useState<AgentState>('disconnected')
  const [isMicEnabled, setIsMicEnabledState] = useState(true)
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false)
  const [lastUserTranscript, setLastUserTranscript] = useState<string | null>(null)
  const [lastAgentTranscript, setLastAgentTranscript] = useState<string | null>(null)
  const [interimUserTranscript, setInterimUserTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)

  const roomRef = useRef<Room | null>(null)
  const audioElementRef = useRef<HTMLAudioElement | null>(null)

  // Clean up on unmount
  useEffect(() => {
    return () => {
      roomRef.current?.disconnect()
      if (audioElementRef.current) {
        audioElementRef.current.srcObject = null
        audioElementRef.current.remove()
      }
    }
  }, [])

  const connect = useCallback(async () => {
    if (roomRef.current) return

    setError(null)
    setAgentState('connecting')

    try {
      // Get token from backend
      const response = await apiCall('/livekit/token', { method: 'POST' })
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || `Token request failed: ${response.status}`)
      }
      const { token, url } = await response.json()

      // Create and connect room
      const room = new Room()
      roomRef.current = room

      // Track subscribed — attach agent audio to an <audio> element
      room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => {
        if (track.kind === Track.Kind.Audio) {
          let el = audioElementRef.current
          if (!el) {
            el = document.createElement('audio')
            el.autoplay = true
            el.style.display = 'none'
            document.body.appendChild(el)
            audioElementRef.current = el
          }
          track.attach(el)
        }
      })

      room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
        if (track.kind === Track.Kind.Audio) {
          track.detach()
        }
      })

      // Agent state via participant attributes
      room.on(RoomEvent.ParticipantAttributesChanged, (_changed: Record<string, string>, participant: Participant) => {
        const state = participant.attributes?.['lk.agent.state']
        if (state) {
          setAgentState(state as AgentState)
          setIsAgentSpeaking(state === 'speaking')
        }
      })

      // Transcription events
      room.on(RoomEvent.TranscriptionReceived, (segments: TranscriptionSegment[], participant?: Participant) => {
        for (const seg of segments) {
          const text = seg.text.trim()
          if (!text) continue

          const isAgent = participant?.identity !== room.localParticipant.identity

          if (isAgent) {
            // Agent transcript
            if (seg.final) {
              setLastAgentTranscript(text)
            }
          } else {
            // User transcript
            if (seg.final) {
              setInterimUserTranscript('')
              setLastUserTranscript(text)
            } else {
              setInterimUserTranscript(text)
            }
          }
        }
      })

      room.on(RoomEvent.Disconnected, () => {
        setIsConnected(false)
        setAgentState('disconnected')
        setIsAgentSpeaking(false)
        roomRef.current = null
      })

      // Connect
      await room.connect(url, token)
      await room.localParticipant.setMicrophoneEnabled(true)

      setIsConnected(true)
      setIsMicEnabledState(true)
      setAgentState('listening')
    } catch (err: any) {
      console.error('[LiveKit] Connection error:', err)
      setError(err.message || 'Failed to connect')
      setAgentState('disconnected')
      roomRef.current = null
    }
  }, [])

  const disconnect = useCallback(() => {
    if (roomRef.current) {
      roomRef.current.disconnect()
      roomRef.current = null
    }
    if (audioElementRef.current) {
      audioElementRef.current.srcObject = null
      audioElementRef.current.remove()
      audioElementRef.current = null
    }
    setIsConnected(false)
    setAgentState('disconnected')
    setIsAgentSpeaking(false)
    setInterimUserTranscript('')
  }, [])

  const setMicEnabled = useCallback((enabled: boolean) => {
    if (roomRef.current) {
      roomRef.current.localParticipant.setMicrophoneEnabled(enabled)
      setIsMicEnabledState(enabled)
    }
  }, [])

  return {
    isConnected,
    agentState,
    connect,
    disconnect,
    setMicEnabled,
    isMicEnabled,
    isAgentSpeaking,
    lastUserTranscript,
    lastAgentTranscript,
    interimUserTranscript,
    error,
  }
}

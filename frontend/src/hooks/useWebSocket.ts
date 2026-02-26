import { useState, useEffect, useRef, useCallback } from 'react'
import { supabase } from '../lib/supabase'

type Status = 'idle' | 'connecting' | 'connected' | 'thinking' | 'error' | 'auth_error'

export interface NotificationData {
  notification_type: 'announcement' | 'activity' | 'team_activity'
  message: string
  activity: {
    id: string
    type: string
    actor_name: string
    detail: string
    created_at: string
  }
}

export interface ProvisioningStatus {
  step: 'creating_assistant' | 'uploading_docs' | 'verifying' | 'creating_thread' | 'complete'
  message: string
  progress: number
  total: number
}

interface UseWebSocketReturn {
  isConnected: boolean
  status: Status
  sendText: (text: string, modelId?: string) => void
  lastResponse: string | null
  lastNotification: NotificationData | null
  provisioningStatus: ProvisioningStatus | null
  switchThread: (threadId: string) => void
  createNewThread: () => Promise<string | null>
  isStreaming: boolean
  streamingContent: string
}

export function useWebSocket(enabled: boolean = true): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false)
  const [status, setStatus] = useState<Status>('idle')
  const [lastResponse, setLastResponse] = useState<string | null>(null)
  const [lastNotification, setLastNotification] = useState<NotificationData | null>(null)
  const [provisioningStatus, setProvisioningStatus] = useState<ProvisioningStatus | null>(null)

  // Streaming state
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const isStreamingRef = useRef(false)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number>()
  const enabledRef = useRef(enabled)
  enabledRef.current = enabled

  const connect = useCallback(async () => {
    if (!enabledRef.current) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const { data: { session } } = await supabase.auth.getSession()

    if (!session?.access_token) {
      // Not authenticated yet — stay idle, don't log error
      return
    }

    const token = session.access_token

    const baseWsUrl = import.meta.env.DEV
      ? 'ws://localhost:8000/ws'
      : 'wss://api.activateyourvoice.tech/ws'
    const wsUrl = `${baseWsUrl}?mode=chat&token=${encodeURIComponent(token)}`

    setStatus('connecting')
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      setIsConnected(true)
      setStatus('connected')
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)

        switch (message.type) {
          case 'status':
            setStatus(message.data as Status)
            break

          case 'response':
            setLastResponse(message.data)
            isStreamingRef.current = false
            setIsStreaming(false)
            setStreamingContent('')
            break

          case 'response_delta':
            if (!isStreamingRef.current) {
              isStreamingRef.current = true
              setIsStreaming(true)
              setStreamingContent(message.data || '')
            } else {
              setStreamingContent(prev => prev + (message.data || ''))
            }
            break

          case 'response_end':
            setLastResponse(message.data)
            isStreamingRef.current = false
            setIsStreaming(false)
            setStreamingContent('')
            break

          case 'error':
            console.error('Server error:', message.data)
            setStatus('error')
            isStreamingRef.current = false
            setIsStreaming(false)
            setStreamingContent('')
            break

          case 'notification':
            setLastNotification(message.data as NotificationData)
            break

          case 'provisioning':
            const pData = message.data as ProvisioningStatus
            setProvisioningStatus(pData)
            if (pData.step === 'complete') {
              // Clear after a short delay so the UI can show "Ready!"
              setTimeout(() => setProvisioningStatus(null), 1500)
            }
            break

          case 'thread_switched':
            console.log('Thread switched to:', message.data)
            break

          case 'thread_created':
            console.log('Thread created:', message.data)
            break
        }
      } catch (e) {
        console.error('Failed to parse message:', e)
      }
    }

    ws.onclose = (event) => {
      setIsConnected(false)
      isStreamingRef.current = false
      setIsStreaming(false)
      setStreamingContent('')

      if (event.code === 4001) {
        console.error('WebSocket auth failed: Invalid or missing token')
        setStatus('auth_error')
        return
      }

      setStatus('idle')
      console.log('WebSocket disconnected', event.code, event.reason)

      // Only reconnect if still enabled
      if (enabledRef.current) {
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect()
        }, 3000)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setStatus('error')
    }

    wsRef.current = ws
  }, [])

  useEffect(() => {
    if (enabled) {
      connect()
    } else {
      // Disconnect when disabled (e.g. user logs out)
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      wsRef.current?.close()
      wsRef.current = null
      setIsConnected(false)
      setStatus('idle')
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      wsRef.current?.close()
    }
  }, [connect, enabled])

  const sendText = useCallback((text: string, modelId?: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected')
      return
    }

    const msg: Record<string, string> = { type: 'text_in', text }
    if (modelId) msg.model_id = modelId

    wsRef.current.send(JSON.stringify(msg))
  }, [])

  const switchThread = useCallback((threadId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'switch_thread',
        thread_id: threadId
      }))
    }
  }, [])

  const createNewThread = useCallback((): Promise<string | null> => {
    return new Promise((resolve) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const handler = (event: MessageEvent) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'thread_created') {
              wsRef.current?.removeEventListener('message', handler)
              resolve(data.data)
            }
          } catch {
            // Ignore parse errors
          }
        }
        wsRef.current.addEventListener('message', handler)
        wsRef.current.send(JSON.stringify({ type: 'new_thread' }))

        setTimeout(() => {
          wsRef.current?.removeEventListener('message', handler)
          resolve(null)
        }, 5000)
      } else {
        resolve(null)
      }
    })
  }, [])

  return {
    isConnected,
    status,
    sendText,
    lastResponse,
    lastNotification,
    provisioningStatus,
    switchThread,
    createNewThread,
    isStreaming,
    streamingContent,
  }
}

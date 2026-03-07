import { useState, useEffect, useCallback, useRef } from 'react'

const getWsUrl = () => {
  if (typeof window === 'undefined') return 'ws://localhost:8000/ws/processing'
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  // If we are served from Vite on port 5173, point to backend 8000
  // Otherwise use the same host (e.g. for production deployments)
  const host = window.location.port === '5173' || window.location.port === '3000' 
    ? `${window.location.hostname}:8000` 
    : window.location.host
  return `${protocol}//${host}/ws/processing`
}

export function useWebSocket(url = getWsUrl()) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const [messages, setMessages] = useState([])
  const wsRef = useRef(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(url)

    ws.onopen = () => {
      setIsConnected(true)
      console.log('WebSocket connected')
    }

    ws.onclose = () => {
      setIsConnected(false)
      console.log('WebSocket disconnected')
      // Reconnect after 3 seconds
      setTimeout(connect, 3000)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setLastMessage(data)
        setMessages(prev => [...prev.slice(-50), data])
      } catch {
        setLastMessage(event.data)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    wsRef.current = ws
  }, [url])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data))
    }
  }, [])

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return { isConnected, lastMessage, messages, send }
}

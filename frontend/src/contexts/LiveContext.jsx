/**
 * TRACE — Live events (DEVELOPMENT.md Phase 7 step 4)
 * One WebSocket per signed-in tab, at /api/v1/ws. The server pushes only
 * "something changed" events — { type: 'notification' } or
 * { type: 'discussion', task_id } — and listeners refetch through the REST API.
 * Reconnects with a growing delay; a missed event is recovered on the next load.
 */

import { createContext, useCallback, useContext, useEffect, useRef } from 'react'
import { useAuth } from '@/contexts/AuthContext'

const LiveContext = createContext({ subscribe: () => () => {} })

export function LiveProvider({ children }) {
  const { isAuthenticated } = useAuth()
  const listeners = useRef(new Set())

  useEffect(() => {
    if (!isAuthenticated) return undefined
    let ws = null
    let retry = null
    let delay = 2000
    let closed = false

    const connect = () => {
      const token = localStorage.getItem('trace_access_token')
      if (!token || closed) return
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${window.location.host}/api/v1/ws?token=${encodeURIComponent(token)}`)
      ws.onopen = () => { delay = 2000 }
      ws.onmessage = (msg) => {
        let event
        try { event = JSON.parse(msg.data) } catch { return }
        listeners.current.forEach((fn) => fn(event))
      }
      ws.onclose = () => {
        if (closed) return
        retry = setTimeout(connect, delay)
        delay = Math.min(delay * 2, 60000)
      }
    }
    connect()
    return () => {
      closed = true
      clearTimeout(retry)
      ws?.close()
    }
  }, [isAuthenticated])

  const subscribe = useCallback((fn) => {
    listeners.current.add(fn)
    return () => listeners.current.delete(fn)
  }, [])

  return <LiveContext.Provider value={{ subscribe }}>{children}</LiveContext.Provider>
}

/** Call `handler(event)` for every live event while the component is mounted. */
export function useLiveEvents(handler) {
  const { subscribe } = useContext(LiveContext)
  const ref = useRef(handler)
  useEffect(() => { ref.current = handler })
  useEffect(() => subscribe((event) => ref.current(event)), [subscribe])
}

import { useEffect, useRef, useCallback } from 'react';

export type WsEvent =
  | { type: 'task_update'; task: Record<string, unknown> }
  | { type: 'message'; message: Record<string, unknown> }
  | { type: 'log'; level: string; text: string };

export function useWebSocket(onEvent: (e: WsEvent) => void) {
  const ws = useRef<WebSocket | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws/events`);

    socket.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as WsEvent;
        onEventRef.current(data);
      } catch {}
    };

    socket.onclose = () => {
      // Reconnect after 3s
      setTimeout(connect, 3000);
    };

    socket.onerror = () => {
      socket.close();
    };

    // Keep-alive ping every 30s
    const ping = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send('ping');
      }
    }, 30000);

    socket.addEventListener('close', () => clearInterval(ping));
    ws.current = socket;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      ws.current?.close();
    };
  }, [connect]);
}

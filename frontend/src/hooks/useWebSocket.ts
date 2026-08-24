import { useEffect, useRef, useState, useCallback } from 'react';
import type { WSMessage } from '../types';

interface UseWebSocketOptions {
  showId: string | null;
  onFullState?: (seats: any[]) => void;
  onUpdates?: (updates: any[]) => void;
  onReconnect?: () => void;
}

export const useWebSocket = ({
  showId,
  onFullState,
  onUpdates,
  onReconnect,
}: UseWebSocketOptions) => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const isFirstConnect = useRef<boolean>(true);
  const intentionalCloseRef = useRef<boolean>(false);

  const connect = useCallback(() => {
    if (!showId) return;

    let wsHost = import.meta.env.VITE_WS_BASE_URL;
    if (!wsHost) {
      const apiBase = import.meta.env.VITE_API_BASE_URL;
      if (apiBase) {
        const url = new URL(apiBase);
        wsHost = `${url.protocol === 'https:' ? 'wss:' : 'ws:'}//${url.host}`;
      } else {
        wsHost = window.location.hostname === 'localhost' ? 'ws://localhost:8005' : `wss://${window.location.host}`;
      }
    }
    const wsUrl = `${wsHost}/ws/shows/${showId}/seats/`;

    console.log(`Connecting to WebSocket: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;
    intentionalCloseRef.current = false;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      if (!isFirstConnect.current && onReconnect) {
        onReconnect();
      }
      isFirstConnect.current = false;
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        if (msg.type === 'seat_map_state' && msg.seats && onFullState) {
          onFullState(msg.seats);
        } else if (msg.type === 'seat_updates' && msg.updates && onUpdates) {
          onUpdates(msg.updates);
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      if (intentionalCloseRef.current) {
        console.log('WebSocket closed intentionally.');
        return;
      }
      console.log('WebSocket disconnected. Attempting reconnect in 3s...');
      setIsConnected(false);
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connect();
      }, 3000);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      ws.close();
    };
  }, [showId, onFullState, onUpdates, onReconnect]);

  useEffect(() => {
    isFirstConnect.current = true;
    connect();

    return () => {
      intentionalCloseRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  return { isConnected };
};

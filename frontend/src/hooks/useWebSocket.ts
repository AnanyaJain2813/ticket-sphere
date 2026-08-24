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

  const connect = useCallback(() => {
    if (!showId) return;

    const wsHost = import.meta.env.VITE_WS_BASE_URL || (window.location.hostname === 'localhost' ? 'ws://localhost:8000' : `wss://${window.location.host}`);
    const wsUrl = `${wsHost}/ws/shows/${showId}/seats/`;

    console.log(`Connecting to WebSocket: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

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

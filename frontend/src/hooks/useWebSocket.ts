'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketClient, createWebSocketClient } from '@/lib/websocket';
import { WSMessage } from '@/types';
import { tokenManager } from '@/lib/api';

interface UseWebSocketOptions {
  conversationId: string;
  stream?: boolean;
  onMessage?: (message: WSMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoConnect?: boolean;
}

export function useWebSocket({
  conversationId,
  stream = false,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  autoConnect = true,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocketClient | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    const apiKey = tokenManager.getAccessToken();
    if (!apiKey || !conversationId) {
      setError('Missing API key or conversation ID');
      return;
    }

    try {
      wsRef.current = createWebSocketClient(apiKey, conversationId, stream);

      wsRef.current.onConnect(() => {
        setIsConnected(true);
        setError(null);
        onConnect?.();
      });

      wsRef.current.onDisconnect(() => {
        setIsConnected(false);
        onDisconnect?.();
      });

      wsRef.current.onMessage((message) => {
        onMessage?.(message);
      });

      wsRef.current.onError((err) => {
        setError('WebSocket connection error');
        onError?.(err);
      });

      await wsRef.current.connect();
    } catch (err) {
      setError('Failed to connect to WebSocket');
      console.error('WebSocket connection error:', err);
    }
  }, [conversationId, stream, onConnect, onDisconnect, onMessage, onError]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
      setIsConnected(false);
    }
  }, []);

  const sendMessage = useCallback((content: string, useRag = false) => {
    if (wsRef.current) {
      wsRef.current.sendMessage(content, useRag);
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  useEffect(() => {
    if (autoConnect && conversationId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, conversationId, connect, disconnect]);

  return {
    isConnected,
    error,
    connect,
    disconnect,
    sendMessage,
  };
}

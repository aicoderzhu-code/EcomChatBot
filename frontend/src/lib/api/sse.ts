/**
 * SSE event stream consumer using fetch() + ReadableStream.
 * Supports POST requests with custom headers (unlike EventSource).
 */
import { tokenManager } from './client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface SSEEvent {
  type: string;  // chunk | sources | done | error
  data: Record<string, unknown>;
}

export interface SSEOptions {
  url: string;
  body: Record<string, unknown>;
  onEvent: (event: SSEEvent) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
  signal?: AbortSignal;
}

export async function consumeSSE({ url, body, onEvent, onError, onComplete, signal }: SSEOptions) {
  const token = tokenManager.getAccessToken();
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;

  const response = await fetch(fullUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const text = await response.text();
    const err = new Error(`SSE request failed: ${response.status} ${text}`);
    onError?.(err);
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const segments = buffer.split('\n\n');
      buffer = segments.pop()!;

      for (const segment of segments) {
        if (!segment.trim()) continue;

        const lines = segment.split('\n');
        let eventType = 'message';
        let data = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7);
          } else if (line.startsWith('data: ')) {
            data = line.slice(6);
          }
        }

        if (!data) continue;

        try {
          const parsed = JSON.parse(data);
          onEvent({ type: eventType, data: parsed });
        } catch {
          // skip malformed JSON
        }
      }
    }
  } catch (err) {
    if ((err as Error).name !== 'AbortError') {
      onError?.(err as Error);
    }
  } finally {
    onComplete?.();
  }
}

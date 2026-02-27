'use client';

import { useState, useRef, useCallback } from 'react';
import { Typography, message } from 'antd';
import { PlaygroundChat, PlaygroundConfig, ChatMessage, PlaygroundSettings, MessageMeta } from '@/components/playground';
import { consumeSSE } from '@/lib/api/sse';

const { Title } = Typography;

export default function PlaygroundPage() {
  const [settings, setSettings] = useState<PlaygroundSettings>({
    modelConfigId: null,
    systemPrompt: '',
    useRag: false,
    ragTopK: 3,
  });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const handleClear = () => {
    abortRef.current?.abort();
    setMessages([]);
  };

  const handleSend = useCallback(async () => {
    const content = inputValue.trim();
    if (!content || sending) return;
    if (!settings.modelConfigId) {
      message.warning('请先选择模型');
      return;
    }

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
    };

    const assistantId = `assistant-${Date.now()}`;
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      streaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInputValue('');
    setSending(true);

    const conversationHistory = messages
      .filter((m) => !m.streaming)
      .map((m) => ({ role: m.role, content: m.content }));

    const controller = new AbortController();
    abortRef.current = controller;

    let ragSources: MessageMeta['ragSources'] = undefined;

    await consumeSSE({
      url: '/playground/chat-stream',
      body: {
        message: content,
        model_config_id: settings.modelConfigId,
        system_prompt: settings.systemPrompt || undefined,
        use_rag: settings.useRag,
        rag_top_k: settings.ragTopK,
        conversation_history: conversationHistory,
      },
      signal: controller.signal,
      onEvent: (event) => {
        switch (event.type) {
          case 'chunk': {
            const chunk = event.data.content as string;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + chunk }
                  : m
              )
            );
            break;
          }
          case 'sources':
            ragSources = event.data.sources as MessageMeta['ragSources'];
            break;
          case 'done': {
            const meta: MessageMeta = {
              model: event.data.model as string,
              provider: event.data.provider as string,
              inputTokens: event.data.input_tokens as number,
              outputTokens: event.data.output_tokens as number,
              responseTimeMs: event.data.response_time_ms as number,
              ragSources,
            };
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, streaming: false, meta }
                  : m
              )
            );
            break;
          }
          case 'error':
            message.error((event.data.message as string) || 'Stream error');
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, streaming: false, content: m.content || 'Error occurred' }
                  : m
              )
            );
            break;
        }
      },
      onError: (err) => {
        message.error(err.message);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, streaming: false, content: m.content || 'Request failed' }
              : m
          )
        );
      },
      onComplete: () => {
        setSending(false);
        abortRef.current = null;
      },
    });
  }, [inputValue, sending, settings, messages]);

  return (
    <div className="h-[calc(100vh-64px-48px)] flex flex-col">
      <div className="px-6 pt-4 pb-2">
        <Title level={4} className="!mb-3">LLM Playground</Title>
        <PlaygroundConfig value={settings} onChange={setSettings} />
      </div>
      <div className="flex-1 min-h-0 mx-6 mb-4 border rounded-lg bg-white overflow-hidden">
        <PlaygroundChat
          messages={messages}
          inputValue={inputValue}
          onInputChange={setInputValue}
          onSend={handleSend}
          sending={sending}
          onClear={handleClear}
        />
      </div>
    </div>
  );
}

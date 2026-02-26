'use client';

import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { message, Spin } from 'antd';
import {
  ConversationList,
  ChatWindow,
  RightPanel,
} from '@/components/chat';
import { conversationApi } from '@/lib/api';
import { platformApi } from '@/lib/api/platform';
import { useConversationStore } from '@/store/conversationStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Message } from '@/types';

export default function ChatPage() {
  const searchParams = useSearchParams();
  const initialId = searchParams.get('id');

  const [selectedId, setSelectedId] = useState<string | null>(initialId);
  const [inputValue, setInputValue] = useState('');
  const [searchValue, setSearchValue] = useState('');
  const [sending, setSending] = useState(false);

  // Zustand selector — 细粒度订阅，避免全量重渲染
  const conversations = useConversationStore(s => s.conversations);
  const currentConversation = useConversationStore(s => s.currentConversation);
  const messages = useConversationStore(s => s.messages);
  const isLoading = useConversationStore(s => s.isLoading);
  const pagination = useConversationStore(s => s.pagination);
  const statusFilter = useConversationStore(s => s.statusFilter);
  const ragSources = useConversationStore(s => s.ragSources);
  const fetchConversations = useConversationStore(s => s.fetchConversations);
  const selectConversation = useConversationStore(s => s.selectConversation);
  const addMessage = useConversationStore(s => s.addMessage);
  const closeConversation = useConversationStore(s => s.closeConversation);
  const setStatusFilter = useConversationStore(s => s.setStatusFilter);
  const setWsStatus = useConversationStore(s => s.setWsStatus);
  const startStreamingMessage = useConversationStore(s => s.startStreamingMessage);
  const appendStreamChunk = useConversationStore(s => s.appendStreamChunk);
  const finalizeStreamingMessage = useConversationStore(s => s.finalizeStreamingMessage);
  const setRagSources = useConversationStore(s => s.setRagSources);
  const takeoverConversation = useConversationStore(s => s.takeoverConversation);

  const streamingIdRef = useRef<string | null>(null);

  // 用 ref 持有最新的 fetchConversations，避免 effect 依赖函数引用导致无限重渲染
  const fetchConversationsRef = useRef(fetchConversations);
  fetchConversationsRef.current = fetchConversations;

  // Initial load + 30s polling（空依赖，只挂载一次）
  useEffect(() => {
    fetchConversationsRef.current();
    const timer = setInterval(() => fetchConversationsRef.current(), 30000);
    return () => clearInterval(timer);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-fetch when filter changes
  useEffect(() => {
    fetchConversations({ page: 1 });
  }, [statusFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load conversation detail when selected
  useEffect(() => {
    if (selectedId) {
      selectConversation(selectedId);
      setRagSources([]);
    }
  }, [selectedId]); // eslint-disable-line react-hooks/exhaustive-deps

  // WebSocket
  const { isConnected, sendMessage: wsSend } = useWebSocket({
    conversationId: selectedId || '',
    stream: true,
    autoConnect: !!selectedId,
    onConnect: () => setWsStatus('connected'),
    onDisconnect: () => setWsStatus('disconnected'),
    onMessage: (msg) => {
      if (msg.type === 'stream') {
        const chunk = msg.chunk ?? msg.content ?? '';
        if (!streamingIdRef.current) {
          streamingIdRef.current = startStreamingMessage(selectedId!);
        }
        appendStreamChunk(streamingIdRef.current, chunk);
        if (msg.is_final) {
          finalizeStreamingMessage(streamingIdRef.current);
          streamingIdRef.current = null;
        }
      } else if (msg.type === 'message') {
        if (streamingIdRef.current) {
          finalizeStreamingMessage(streamingIdRef.current);
          streamingIdRef.current = null;
        }
        if (msg.role === 'assistant' && msg.content) {
          const newMsg: Message = {
            id: Date.now(),
            message_id: `ws-${Date.now()}`,
            conversation_id: selectedId!,
            role: 'assistant',
            content: msg.content,
            created_at: msg.timestamp || new Date().toISOString(),
            input_tokens: msg.tokens?.input || 0,
            output_tokens: msg.tokens?.output || 0,
          };
          addMessage(newMsg);
        }
      } else if (msg.type === 'metadata' && msg.sources) {
        setRagSources(
          msg.sources.map((s) => ({
            knowledge_id: s.knowledge_id,
            title: s.title,
            content: '',
            score: s.score,
            source: s.title,
          }))
        );
      } else if (msg.type === 'error') {
        message.error(msg.content || '消息处理出错');
      }
    },
  });

  const handleSelectConversation = (id: string) => {
    setSelectedId(id);
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !selectedId) return;

    const userMsg: Message = {
      id: Date.now(),
      message_id: `msg-${Date.now()}`,
      conversation_id: selectedId,
      role: 'user',
      content: inputValue,
      created_at: new Date().toISOString(),
      input_tokens: 0,
      output_tokens: 0,
    };
    addMessage(userMsg);
    const content = inputValue;
    setInputValue('');

    if (currentConversation?.status === 'waiting') {
      // Human takeover mode
      setSending(true);
      try {
        // 拼多多平台会话走平台回复 API，其他走通用 REST
        if (currentConversation.platform_type === 'pinduoduo') {
          const response = await platformApi.sendPlatformMessage(selectedId, content);
          if (!response.success) {
            message.error('发送失败');
          }
        } else {
          const response = await conversationApi.sendMessage(selectedId, { content });
          if (!response.success) {
            message.error(response.error?.message || '发送失败');
          }
        }
      } catch {
        message.error('发送消息失败');
      } finally {
        setSending(false);
      }
    } else {
      // AI mode: use WebSocket
      wsSend(content);
    }
  };

  const handleCloseConversation = async () => {
    if (!selectedId) return;
    await closeConversation(selectedId);
    message.success('会话已结束');
  };

  const handleTakeover = async () => {
    if (!selectedId) return;
    await takeoverConversation(selectedId);
    message.success('已接管会话，切换至人工模式');
  };

  const handleStatusFilterChange = (status: 'all' | 'active' | 'waiting' | 'closed') => {
    setStatusFilter(status);
  };

  const handlePageChange = (page: number) => {
    fetchConversations({ page });
  };

  // Filter by search locally
  const filteredConversations = conversations.filter((c) => {
    if (!searchValue) return true;
    const s = searchValue.toLowerCase();
    return (
      c.conversation_id.toLowerCase().includes(s) ||
      c.user_external_id.toLowerCase().includes(s) ||
      c.last_message_preview?.toLowerCase().includes(s)
    );
  });

  if (isLoading && conversations.length === 0) {
    return (
      <div className="h-[calc(100vh-64px-48px)] flex items-center justify-center">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-64px-48px)] flex bg-white rounded-lg overflow-hidden shadow">
      {/* Conversation List */}
      <div className="w-80 flex-shrink-0">
        <ConversationList
          conversations={filteredConversations}
          selectedId={selectedId}
          onSelect={handleSelectConversation}
          searchValue={searchValue}
          onSearchChange={setSearchValue}
          statusFilter={statusFilter}
          onStatusFilterChange={handleStatusFilterChange}
          pagination={pagination}
          onPageChange={handlePageChange}
          loading={isLoading}
        />
      </div>

      {/* Chat Window */}
      <ChatWindow
        conversation={currentConversation}
        messages={messages}
        inputValue={inputValue}
        onInputChange={setInputValue}
        onSend={handleSendMessage}
        onClose={handleCloseConversation}
        onTakeover={handleTakeover}
        sending={sending}
        loading={isLoading && !!selectedId && !currentConversation}
        wsConnected={isConnected}
      />

      {/* Right Panel */}
      <RightPanel user={currentConversation?.user || null} ragSources={ragSources} />
    </div>
  );
}

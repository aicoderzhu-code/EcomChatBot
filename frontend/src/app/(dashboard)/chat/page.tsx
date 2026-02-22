'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { message, Spin } from 'antd';
import {
  ConversationList,
  ChatWindow,
  RightPanel,
} from '@/components/chat';
import { conversationApi } from '@/lib/api';
import {
  Conversation,
  ConversationDetail,
  Message,
  User,
  KnowledgeSearchResult,
} from '@/types';

export default function ChatPage() {
  const searchParams = useSearchParams();
  const initialId = searchParams.get('id');

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(initialId);
  const [currentConversation, setCurrentConversation] = useState<ConversationDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [searchValue, setSearchValue] = useState('');
  const [loading, setLoading] = useState(true);
  const [conversationLoading, setConversationLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [ragSources, setRagSources] = useState<KnowledgeSearchResult[]>([]);

  // Load conversations list
  const loadConversations = useCallback(async () => {
    try {
      const response = await conversationApi.list({ page: 1, size: 50 });
      if (response.success && response.data) {
        setConversations(response.data.items || []);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
      message.error('加载会话列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Load conversation details when selected
  useEffect(() => {
    if (!selectedId) {
      setCurrentConversation(null);
      setMessages([]);
      setUser(null);
      setRagSources([]);
      return;
    }

    const loadConversationDetail = async () => {
      setConversationLoading(true);
      try {
        const response = await conversationApi.get(selectedId);
        if (response.success && response.data) {
          const detail = response.data;
          setCurrentConversation(detail);
          setMessages(detail.messages || []);
          setUser(detail.user || null);
          // TODO: Load RAG sources if available
          setRagSources([]);
        }
      } catch (err) {
        console.error('Failed to load conversation:', err);
        message.error('加载会话详情失败');
      } finally {
        setConversationLoading(false);
      }
    };

    loadConversationDetail();
  }, [selectedId]);

  const handleSelectConversation = (id: string) => {
    setSelectedId(id);
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !selectedId) return;

    const userMessage: Message = {
      id: Date.now(),
      message_id: `msg-${Date.now()}`,
      conversation_id: selectedId,
      role: 'user',
      content: inputValue,
      created_at: new Date().toISOString(),
      input_tokens: 0,
      output_tokens: 0,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setSending(true);

    try {
      const response = await conversationApi.sendMessage(selectedId, {
        content: inputValue,
      });

      if (response.success && response.data) {
        // Add the AI response
        setMessages((prev) => [...prev, response.data as Message]);
      } else {
        message.error(response.error?.message || '发送失败');
      }
    } catch (err) {
      console.error('Failed to send message:', err);
      message.error('发送消息失败');
    } finally {
      setSending(false);
    }
  };

  const handleCloseConversation = async () => {
    if (!selectedId) return;

    try {
      const response = await conversationApi.close(selectedId);
      if (response.success) {
        // Update conversation status in list
        setConversations((prev) =>
          prev.map((c) =>
            c.conversation_id === selectedId ? { ...c, status: 'closed' as const } : c
          )
        );
        if (currentConversation) {
          setCurrentConversation({ ...currentConversation, status: 'closed' });
        }
        message.success('会话已结束');
      }
    } catch (err) {
      console.error('Failed to close conversation:', err);
      message.error('关闭会话失败');
    }
  };

  const handleTakeover = () => {
    message.info('已接管会话，切换至人工模式');
  };

  // Filter conversations by search
  const filteredConversations = conversations.filter((c) => {
    if (!searchValue) return true;
    const search = searchValue.toLowerCase();
    return (
      c.conversation_id.toLowerCase().includes(search) ||
      c.user_external_id.toLowerCase().includes(search) ||
      c.last_message_preview?.toLowerCase().includes(search)
    );
  });

  if (loading) {
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
        loading={conversationLoading}
      />

      {/* Right Panel */}
      <RightPanel user={user} ragSources={ragSources} />
    </div>
  );
}

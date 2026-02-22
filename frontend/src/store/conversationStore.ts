import { create } from 'zustand';
import { conversationApi } from '@/lib/api';
import { Conversation, ConversationDetail, Message } from '@/types';

interface ConversationState {
  conversations: Conversation[];
  currentConversation: ConversationDetail | null;
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  pagination: {
    page: number;
    size: number;
    total: number;
    pages: number;
  };

  fetchConversations: (params?: { status?: string; page?: number }) => Promise<void>;
  fetchConversation: (conversationId: string) => Promise<void>;
  selectConversation: (conversationId: string) => Promise<void>;
  addMessage: (message: Message) => void;
  updateMessage: (messageId: string, content: string) => void;
  closeConversation: (conversationId: string) => Promise<void>;
  clearCurrentConversation: () => void;
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  conversations: [],
  currentConversation: null,
  messages: [],
  isLoading: false,
  error: null,
  pagination: {
    page: 1,
    size: 20,
    total: 0,
    pages: 0,
  },

  fetchConversations: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await conversationApi.list({
        page: params?.page || get().pagination.page,
        size: get().pagination.size,
        status: params?.status,
      });

      if (response.success && response.data) {
        set({
          conversations: response.data.items,
          pagination: {
            page: response.data.page,
            size: response.data.size,
            total: response.data.total,
            pages: response.data.pages,
          },
          isLoading: false,
        });
      } else {
        set({
          error: response.error?.message || '加载会话列表失败',
          isLoading: false,
        });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '加载会话列表失败',
        isLoading: false,
      });
    }
  },

  fetchConversation: async (conversationId: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await conversationApi.get(conversationId);
      if (response.success && response.data) {
        set({
          currentConversation: response.data,
          messages: response.data.messages || [],
          isLoading: false,
        });
      } else {
        set({
          error: response.error?.message || '加载会话详情失败',
          isLoading: false,
        });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '加载会话详情失败',
        isLoading: false,
      });
    }
  },

  selectConversation: async (conversationId: string) => {
    await get().fetchConversation(conversationId);
  },

  addMessage: (message: Message) => {
    set((state) => ({
      messages: [...state.messages, message],
    }));
  },

  updateMessage: (messageId: string, content: string) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.message_id === messageId ? { ...msg, content } : msg
      ),
    }));
  },

  closeConversation: async (conversationId: string) => {
    try {
      const response = await conversationApi.close(conversationId);
      if (response.success) {
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.conversation_id === conversationId
              ? { ...conv, status: 'closed' as const }
              : conv
          ),
          currentConversation: state.currentConversation?.conversation_id === conversationId
            ? { ...state.currentConversation, status: 'closed' as const }
            : state.currentConversation,
        }));
      }
    } catch (error) {
      console.error('Failed to close conversation:', error);
    }
  },

  clearCurrentConversation: () => {
    set({ currentConversation: null, messages: [] });
  },
}));

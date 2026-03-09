import apiClient from './client';
import {
  ApiResponse,
  Conversation,
  PaginatedResponse,
} from '@/types';

// Backend response structures
export interface ConversationStats {
  total_conversations: number;
  active_conversations: number;
  closed_conversations: number;
  avg_messages_per_conversation: number;
  total_messages: number;
  total_tokens: number;
}

export interface ResponseTimeStats {
  avg_response_time: number;
  min_response_time: number;
  max_response_time: number;
  p50_response_time: number;
  p95_response_time: number;
  p99_response_time: number;
}

export interface SatisfactionStats {
  avg_satisfaction: number;
  total_ratings: number;
  distribution: Record<string, number>;
  satisfaction_rate: number;
}

export interface DashboardResponse {
  conversation_stats: ConversationStats;
  response_time_stats: ResponseTimeStats;
  satisfaction_stats: SatisfactionStats;
  time_range: string;
}

// Simplified structure for frontend use
export interface DashboardSummary {
  total_conversations: number;
  active_conversations: number;
  completed_conversations: number;
  avg_response_time: number;
  total_messages: number;
  satisfaction_score: number;
  conversation_change: number;
  message_change: number;
}

export interface HourlyTrend {
  hour: string;
  conversations: number;
  messages: number;
}

export const dashboardApi = {
  // Get dashboard summary
  getSummary: async (timeRange: string = '24h'): Promise<ApiResponse<DashboardSummary>> => {
    try {
      const response = await apiClient.get<ApiResponse<DashboardResponse>>('/monitor/dashboard', {
        params: { time_range: timeRange },
      });

      if (response.data.success && response.data.data) {
        const data = response.data.data;
        // Transform to simplified structure
        return {
          success: true,
          data: {
            total_conversations: data.conversation_stats.total_conversations,
            active_conversations: data.conversation_stats.active_conversations,
            completed_conversations: data.conversation_stats.closed_conversations,
            avg_response_time: data.response_time_stats.avg_response_time,
            total_messages: data.conversation_stats.total_messages,
            satisfaction_score: data.satisfaction_stats.avg_satisfaction,
            conversation_change: 0, // Not provided by API
            message_change: 0, // Not provided by API
          },
          error: null,
        };
      }
      return { success: false, data: null, error: response.data.error };
    } catch (error) {
      console.error('Failed to get dashboard summary:', error);
      return {
        success: false,
        data: null,
        error: { code: 'FETCH_ERROR', message: '获取数据失败' }
      };
    }
  },

  // Get hourly trend
  getHourlyTrend: async (hours: number = 24): Promise<ApiResponse<HourlyTrend[]>> => {
    try {
      const response = await apiClient.get<ApiResponse<HourlyTrend[]>>('/monitor/trend/hourly', {
        params: { hours },
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get hourly trend:', error);
      return {
        success: false,
        data: [],
        error: { code: 'FETCH_ERROR', message: '获取趋势数据失败' }
      };
    }
  },

  // Get conversation stats
  getConversationStats: async (): Promise<ApiResponse<ConversationStats>> => {
    try {
      const response = await apiClient.get<ApiResponse<ConversationStats>>('/monitor/conversations');
      return response.data;
    } catch (error) {
      console.error('Failed to get conversation stats:', error);
      return {
        success: false,
        data: null,
        error: { code: 'FETCH_ERROR', message: '获取会话统计失败' }
      };
    }
  },

  // Get recent conversations
  getRecentConversations: async (limit: number = 10): Promise<ApiResponse<PaginatedResponse<Conversation>>> => {
    try {
      const response = await apiClient.get<ApiResponse<PaginatedResponse<Conversation>>>('/conversation/list', {
        params: { page: 1, size: limit },
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get recent conversations:', error);
      return {
        success: false,
        data: null,
        error: { code: 'FETCH_ERROR', message: '获取会话列表失败' }
      };
    }
  },
};

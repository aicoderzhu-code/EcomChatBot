import apiClient from './client';
import { ApiResponse } from '@/types';

export interface RetrievalMetrics {
  total_queries: number;
  hit_count: number;
  hit_rate: number;
  avg_match_score: number;
  helpful_count: number;
  unhelpful_count: number;
  days: number;
}

export interface FailedQuery {
  query: string;
  count: number;
  avg_score: number;
  last_queried: string | null;
}

export interface KnowledgeEffectiveness {
  knowledge_id: string;
  title: string;
  use_count: number;
  avg_score: number;
  helpful_count: number;
  unhelpful_count: number;
  helpful_rate: number | null;
}

export interface RetrievalTrend {
  date: string;
  total: number;
  hits: number;
  hit_rate: number;
  avg_score: number;
}

export const ragAnalyticsApi = {
  getMetrics: async (days?: number): Promise<ApiResponse<RetrievalMetrics>> => {
    const response = await apiClient.get<ApiResponse<RetrievalMetrics>>('/rag/analytics/metrics', {
      params: { days },
    });
    return response.data;
  },

  getFailedQueries: async (limit?: number): Promise<ApiResponse<FailedQuery[]>> => {
    const response = await apiClient.get<ApiResponse<FailedQuery[]>>('/rag/analytics/failed-queries', {
      params: { limit },
    });
    return response.data;
  },

  getKnowledgeEffectiveness: async (limit?: number): Promise<ApiResponse<KnowledgeEffectiveness[]>> => {
    const response = await apiClient.get<ApiResponse<KnowledgeEffectiveness[]>>('/rag/analytics/knowledge-effectiveness', {
      params: { limit },
    });
    return response.data;
  },

  getTrends: async (days?: number): Promise<ApiResponse<RetrievalTrend[]>> => {
    const response = await apiClient.get<ApiResponse<RetrievalTrend[]>>('/rag/analytics/trends', {
      params: { days },
    });
    return response.data;
  },

  submitFeedback: async (data: {
    knowledge_id: string;
    conversation_id: string;
    message_id: string;
    query: string;
    helpful: boolean;
    feedback?: string;
  }): Promise<ApiResponse<{ message: string }>> => {
    const response = await apiClient.post<ApiResponse<{ message: string }>>('/rag/feedback', data);
    return response.data;
  },
};

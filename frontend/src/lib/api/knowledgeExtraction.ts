import apiClient from './client';
import { ApiResponse, PaginatedResponse } from '@/types';

export interface KnowledgeCandidate {
  id: number;
  candidate_id: string;
  conversation_id: string;
  question: string;
  answer: string;
  category: string | null;
  confidence_score: number;
  status: string;
  approved_by: string | null;
  created_knowledge_id: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractionMetrics {
  total: number;
  approved: number;
  rejected: number;
  pending: number;
  approval_rate: number;
}

export const knowledgeExtractionApi = {
  listCandidates: async (params?: {
    status?: string;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<KnowledgeCandidate>>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<KnowledgeCandidate>>>('/knowledge/candidates', {
      params,
    });
    return response.data;
  },

  getMetrics: async (): Promise<ApiResponse<ExtractionMetrics>> => {
    const response = await apiClient.get<ApiResponse<ExtractionMetrics>>('/knowledge/candidates/metrics');
    return response.data;
  },

  approve: async (candidateId: string, data?: {
    category?: string;
    question?: string;
    answer?: string;
  }): Promise<ApiResponse<KnowledgeCandidate>> => {
    const response = await apiClient.post<ApiResponse<KnowledgeCandidate>>(
      `/knowledge/candidates/${candidateId}/approve`, data || {},
    );
    return response.data;
  },

  reject: async (candidateId: string, reason: string): Promise<ApiResponse<KnowledgeCandidate>> => {
    const response = await apiClient.post<ApiResponse<KnowledgeCandidate>>(
      `/knowledge/candidates/${candidateId}/reject`, { reason },
    );
    return response.data;
  },

  batchApprove: async (candidateIds: string[]): Promise<ApiResponse<{
    success: string[];
    failed: Array<{ candidate_id: string; error: string }>;
  }>> => {
    const response = await apiClient.post('/knowledge/candidates/batch-approve', {
      candidate_ids: candidateIds,
    });
    return response.data;
  },

  extractFromConversation: async (conversationId: string): Promise<ApiResponse<KnowledgeCandidate[]>> => {
    const response = await apiClient.post<ApiResponse<KnowledgeCandidate[]>>(
      `/knowledge/candidates/extract/${conversationId}`,
    );
    return response.data;
  },
};

import apiClient from './client';
import { ApiResponse, PaginatedResponse } from '@/types';

export interface QAPair {
  id: number;
  qa_id: string;
  knowledge_id: string | null;
  question: string;
  answer: string;
  variations: string[] | null;
  category: string | null;
  priority: number;
  use_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export const qaApi = {
  list: async (params?: {
    category?: string;
    keyword?: string;
    status?: string;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<QAPair>>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<QAPair>>>('/knowledge/qa', { params });
    return response.data;
  },

  get: async (qaId: string): Promise<ApiResponse<QAPair>> => {
    const response = await apiClient.get<ApiResponse<QAPair>>(`/knowledge/qa/${qaId}`);
    return response.data;
  },

  create: async (data: {
    question: string;
    answer: string;
    category?: string;
    priority?: number;
  }): Promise<ApiResponse<QAPair>> => {
    const response = await apiClient.post<ApiResponse<QAPair>>('/knowledge/qa', data);
    return response.data;
  },

  update: async (qaId: string, data: {
    question?: string;
    answer?: string;
    category?: string;
    priority?: number;
    variations?: string[];
    status?: string;
  }): Promise<ApiResponse<QAPair>> => {
    const response = await apiClient.put<ApiResponse<QAPair>>(`/knowledge/qa/${qaId}`, data);
    return response.data;
  },

  delete: async (qaId: string): Promise<ApiResponse<{ message: string }>> => {
    const response = await apiClient.delete<ApiResponse<{ message: string }>>(`/knowledge/qa/${qaId}`);
    return response.data;
  },

  importCsv: async (file: File): Promise<ApiResponse<{
    success_count: number;
    failed_count: number;
    failed_items: Array<{ item: Record<string, string>; error: string }> | null;
  }>> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/knowledge/qa/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  regenerateVariations: async (qaId: string): Promise<ApiResponse<QAPair>> => {
    const response = await apiClient.post<ApiResponse<QAPair>>(`/knowledge/qa/${qaId}/regenerate-variations`);
    return response.data;
  },

  getPopular: async (params?: {
    category?: string;
    limit?: number;
  }): Promise<ApiResponse<QAPair[]>> => {
    const response = await apiClient.get<ApiResponse<QAPair[]>>('/knowledge/qa/popular', { params });
    return response.data;
  },
};

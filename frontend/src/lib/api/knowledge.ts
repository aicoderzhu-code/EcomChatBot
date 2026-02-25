import apiClient from './client';
import {
  ApiResponse,
  PaginatedResponse,
  KnowledgeSearchResult,
} from '@/types';

// Knowledge response from backend
export interface KnowledgeItem {
  id: number;
  knowledge_id: string;
  tenant_id: string;
  knowledge_type: string;
  title: string;
  content: string;
  category: string | null;
  tags: string[];
  source: string | null;
  priority: number;
  is_active: boolean;
  embedding_status: string;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeStats {
  total_documents: number;
  total_chunks: number;
  storage_used: number;
  storage_used_mb: number;
}

export interface KnowledgeSettings {
  embedding_model_id: number | null;
  rerank_model_id: number | null;
  has_indexed_documents: boolean;
}

export const knowledgeApi = {
  list: async (params?: {
    knowledge_type?: string;
    category?: string;
    keyword?: string;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<KnowledgeItem>>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<KnowledgeItem>>>('/knowledge/list', {
      params,
    });
    return response.data;
  },

  get: async (knowledgeId: string): Promise<ApiResponse<KnowledgeItem>> => {
    const response = await apiClient.get<ApiResponse<KnowledgeItem>>(`/knowledge/${knowledgeId}`);
    return response.data;
  },

  create: async (data: {
    knowledge_type: string;
    title: string;
    content: string;
    category?: string;
    tags?: string[];
    source?: string;
    priority?: number;
  }): Promise<ApiResponse<KnowledgeItem>> => {
    const response = await apiClient.post<ApiResponse<KnowledgeItem>>('/knowledge/create', data);
    return response.data;
  },

  update: async (knowledgeId: string, data: {
    title?: string;
    content?: string;
    category?: string;
    tags?: string[];
    priority?: number;
  }): Promise<ApiResponse<KnowledgeItem>> => {
    const response = await apiClient.put<ApiResponse<KnowledgeItem>>(`/knowledge/${knowledgeId}`, data);
    return response.data;
  },

  delete: async (knowledgeId: string): Promise<ApiResponse<{ message: string }>> => {
    const response = await apiClient.delete<ApiResponse<{ message: string }>>(`/knowledge/${knowledgeId}`);
    return response.data;
  },

  search: async (query: string, topK?: number): Promise<ApiResponse<KnowledgeItem[]>> => {
    const response = await apiClient.post<ApiResponse<KnowledgeItem[]>>('/knowledge/search', {
      query,
      top_k: topK || 5,
    });
    return response.data;
  },

  batchImport: async (items: Array<{
    knowledge_type: string;
    title: string;
    content: string;
    category?: string;
    tags?: string[];
    source?: string;
    priority?: number;
  }>): Promise<ApiResponse<{
    success_count: number;
    failed_count: number;
    failed_items: Array<{ title: string; error: string }> | null;
    created: Array<{ knowledge_id: string; title: string }>;
  }>> => {
    const response = await apiClient.post<ApiResponse<{
      success_count: number;
      failed_count: number;
      failed_items: Array<{ title: string; error: string }> | null;
      created: Array<{ knowledge_id: string; title: string }>;
    }>>('/knowledge/batch-import', { knowledge_items: items });
    return response.data;
  },

  // RAG query
  ragQuery: async (params: {
    query: string;
    top_k?: number;
    use_rerank?: boolean;
  }): Promise<ApiResponse<{
    results: KnowledgeSearchResult[];
    query_time: number;
  }>> => {
    const response = await apiClient.post<ApiResponse<{
      results: KnowledgeSearchResult[];
      query_time: number;
    }>>('/knowledge/rag/query', {
      query: params.query,
      top_k: params.top_k || 3,
      use_rerank: params.use_rerank || false,
    });
    return response.data;
  },

  // Knowledge settings
  getSettings: async (): Promise<ApiResponse<KnowledgeSettings>> => {
    const response = await apiClient.get<ApiResponse<KnowledgeSettings>>('/knowledge/settings');
    return response.data;
  },

  updateSettings: async (data: Partial<KnowledgeSettings>): Promise<ApiResponse<KnowledgeSettings>> => {
    const response = await apiClient.put<ApiResponse<KnowledgeSettings>>('/knowledge/settings', data);
    return response.data;
  },

  getStats: async (): Promise<ApiResponse<{ total_documents: number; total_chunks: number; storage_used_mb: number }>> => {
    const response = await apiClient.get<ApiResponse<{ total_documents: number; total_chunks: number; storage_used_mb: number }>>('/knowledge/stats');
    return response.data;
  },

  uploadFile: async (file: File, category?: string): Promise<ApiResponse<KnowledgeItem>> => {
    const formData = new FormData();
    formData.append('file', file);
    if (category) formData.append('category', category);
    const response = await apiClient.post<ApiResponse<KnowledgeItem>>(
      '/knowledge/upload',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return response.data;
  },
};

import apiClient from './client';
import type { ApiResponse, PaginatedResponse } from '@/types';

// ===== 内容生成类型 =====

export interface PromptTemplate {
  id: number;
  tenant_id: string;
  name: string;
  template_type: 'poster' | 'video' | 'title' | 'description';
  content: string;
  variables: string[] | null;
  is_default: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface GenerationTask {
  id: number;
  tenant_id: string;
  product_id: number | null;
  task_type: 'poster' | 'video' | 'title' | 'description';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  prompt: string;
  model_config_id: number | null;
  template_id: number | null;
  params: Record<string, unknown> | null;
  result_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface GeneratedAsset {
  id: number;
  tenant_id: string;
  task_id: number;
  product_id: number | null;
  asset_type: 'image' | 'video' | 'text';
  file_url: string | null;
  content: string | null;
  thumbnail_url: string | null;
  metadata: Record<string, unknown> | null;
  platform_url: string | null;
  is_selected: boolean;
  created_at: string;
  updated_at: string;
}

// ===== API 函数 =====

export const contentApi = {
  // ===== 提示词模板 =====

  async listTemplates(params?: {
    template_type?: string;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<PromptTemplate>>> {
    const { data } = await apiClient.get('/content/templates', { params });
    return data;
  },

  async createTemplate(body: {
    name: string;
    template_type: string;
    content: string;
    variables?: string[];
    is_default?: boolean;
  }): Promise<ApiResponse<PromptTemplate>> {
    const { data } = await apiClient.post('/content/templates', body);
    return data;
  },

  async getTemplate(templateId: number): Promise<ApiResponse<PromptTemplate>> {
    const { data } = await apiClient.get(`/content/templates/${templateId}`);
    return data;
  },

  async updateTemplate(templateId: number, body: {
    name?: string;
    content?: string;
    variables?: string[];
    is_default?: boolean;
  }): Promise<ApiResponse<PromptTemplate>> {
    const { data } = await apiClient.put(`/content/templates/${templateId}`, body);
    return data;
  },

  async deleteTemplate(templateId: number): Promise<ApiResponse<null>> {
    const { data } = await apiClient.delete(`/content/templates/${templateId}`);
    return data;
  },

  // ===== 生成任务 =====

  async createGeneration(body: {
    product_id?: number;
    task_type: string;
    prompt: string;
    template_id?: number;
    model_config_id?: number;
    params?: Record<string, unknown>;
  }): Promise<ApiResponse<GenerationTask>> {
    const { data } = await apiClient.post('/content/generate', body);
    return data;
  },

  async listTasks(params?: {
    task_type?: string;
    product_id?: number;
    status?: string;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<GenerationTask>>> {
    const { data } = await apiClient.get('/content/tasks', { params });
    return data;
  },

  async getTask(taskId: number): Promise<ApiResponse<GenerationTask>> {
    const { data } = await apiClient.get(`/content/tasks/${taskId}`);
    return data;
  },

  async retryTask(taskId: number): Promise<ApiResponse<GenerationTask>> {
    const { data } = await apiClient.post(`/content/tasks/${taskId}/retry`);
    return data;
  },

  // ===== 素材 =====

  async listAssets(params?: {
    task_id?: number;
    product_id?: number;
    asset_type?: string;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<GeneratedAsset>>> {
    const { data } = await apiClient.get('/content/assets', { params });
    return data;
  },

  async uploadAssetToPlatform(body: {
    asset_id: number;
    platform_config_id: number;
  }): Promise<ApiResponse<{ platform_url: string }>> {
    const { data } = await apiClient.post('/content/assets/upload', body);
    return data;
  },
};

import apiClient from './client';
import type { ApiResponse, PaginatedResponse } from '@/types';

// ===== 内容生成类型 =====

export interface ProductPrompt {
  id: number;
  tenant_id: string;
  product_id: number;
  prompt_type: 'image' | 'video' | 'title' | 'description';
  name: string;
  content: string;
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
  prompt_id: number | null;
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
  // ===== 商品提示词 =====

  async listPrompts(params?: {
    product_id?: number;
    prompt_type?: string;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<ProductPrompt>>> {
    const { data } = await apiClient.get('/content/prompts', { params });
    return data;
  },

  async createPrompt(body: {
    product_id: number;
    prompt_type: string;
    name: string;
    content: string;
  }): Promise<ApiResponse<ProductPrompt>> {
    const { data } = await apiClient.post('/content/prompts', body);
    return data;
  },

  async updatePrompt(promptId: number, body: {
    name?: string;
    content?: string;
  }): Promise<ApiResponse<ProductPrompt>> {
    const { data } = await apiClient.put(`/content/prompts/${promptId}`, body);
    return data;
  },

  async deletePrompt(promptId: number): Promise<ApiResponse<null>> {
    const { data } = await apiClient.delete(`/content/prompts/${promptId}`);
    return data;
  },

  // ===== 生成任务 =====

  async createGeneration(body: {
    product_id?: number;
    task_type: string;
    prompt: string;
    prompt_id?: number;
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
    keyword?: string;
    is_selected?: boolean;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<GeneratedAsset>>> {
    const { data } = await apiClient.get('/content/assets', { params });
    return data;
  },

  async deleteAsset(assetId: number): Promise<ApiResponse<null>> {
    const { data } = await apiClient.delete(`/content/assets/${assetId}`);
    return data;
  },

  async toggleAssetSelected(assetId: number): Promise<ApiResponse<GeneratedAsset>> {
    const { data } = await apiClient.put(`/content/assets/${assetId}/selected`);
    return data;
  },

  getAssetDownloadUrl(assetId: number): string {
    return `/api/v1/content/assets/${assetId}/download`;
  },

  async uploadAssetToPlatform(body: {
    asset_id: number;
    platform_config_id: number;
  }): Promise<ApiResponse<{ platform_url: string }>> {
    const { data } = await apiClient.post('/content/assets/upload', body);
    return data;
  },
};

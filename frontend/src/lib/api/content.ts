import apiClient from './client';
import type {
  ApiResponse,
  PaginatedResponse,
  ContentTemplate,
  PlatformMediaSpec,
  TemplateRenderRequest,
  TemplateRenderResponse,
  GenerationTask,
  GeneratedAsset,
  GenerateRequest,
  BatchGenerateRequest,
  ReviewAssetRequest,
  BatchUploadAssetsRequest,
} from '@/types';

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

// 从 types/index.ts 重新导出，保持向后兼容
export type { GenerationTask, GeneratedAsset } from '@/types';

// ===== Provider 能力类型 =====

export interface SizeOption {
  value: string;
  label: string;
}

export interface ImageProviderCapability {
  param_mapping: Record<string, string>;
  supports_batch: boolean;
  max_batch: number;
  size_options: SizeOption[];
  default_size: string;
  response_parser: string;
  extra_body: Record<string, unknown>;
}

export interface DurationOption {
  value: number;
  label: string;
}

export interface VideoProviderCapability {
  param_mapping: Record<string, string>;
  supports_image_url: boolean;
  duration_options: DurationOption[];
  default_duration: number;
}

// ===== API 函数 =====

export const contentApi = {
  // ===== 场景模板 =====

  async listTemplates(params?: {
    category?: 'poster' | 'video';
    scene_type?: string;
    platform?: string;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<ContentTemplate>>> {
    const { data } = await apiClient.get('/content/templates', { params });
    return data;
  },

  async createTemplate(body: {
    name: string;
    category: 'poster' | 'video';
    scene_type: string;
    prompt_template: string;
    variables?: Array<{ key: string; label: string; source: string; required: boolean; default?: string }>;
    style_options?: string[];
    platform_presets?: Record<string, { size: string }>;
    default_params?: Record<string, unknown>;
    thumbnail_url?: string;
  }): Promise<ApiResponse<ContentTemplate>> {
    const { data } = await apiClient.post('/content/templates', body);
    return data;
  },

  async getTemplate(templateId: number): Promise<ApiResponse<ContentTemplate>> {
    const { data } = await apiClient.get(`/content/templates/${templateId}`);
    return data;
  },

  async renderTemplate(
    templateId: number,
    body: TemplateRenderRequest,
  ): Promise<ApiResponse<TemplateRenderResponse>> {
    const { data } = await apiClient.post(`/content/templates/${templateId}/render`, body);
    return data;
  },

  // ===== 平台规范 =====

  async listPlatformSpecs(params?: {
    platform_type?: string;
    media_type?: string;
  }): Promise<ApiResponse<PlatformMediaSpec[]>> {
    const { data } = await apiClient.get('/content/platform-specs', { params });
    return data;
  },

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

  async createGeneration(body: GenerateRequest): Promise<ApiResponse<GenerationTask>> {
    const { data } = await apiClient.post('/content/generate', body);
    return data;
  },

  async batchGenerate(body: BatchGenerateRequest): Promise<ApiResponse<GenerationTask[]>> {
    const { data } = await apiClient.post('/content/batch-generate', body);
    return data;
  },

  async listTasks(params?: {
    task_type?: string;
    product_id?: number;
    status?: string;
    scene_type?: string;
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
    scene_type?: string;
    target_platform?: string;
    review_status?: string;
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

  async reviewAsset(assetId: number, body: ReviewAssetRequest): Promise<ApiResponse<GeneratedAsset>> {
    const { data } = await apiClient.put(`/content/assets/${assetId}/review`, body);
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

  async batchUploadAssets(body: BatchUploadAssetsRequest): Promise<ApiResponse<{
    success: Array<{ asset_id: number; platform_url: string }>;
    failed: Array<{ asset_id: number; error: string }>;
  }>> {
    const { data } = await apiClient.post('/content/assets/batch-upload', body);
    return data;
  },

  // ===== Provider 能力 =====

  async getProviderCapabilities<T = Record<string, ImageProviderCapability | VideoProviderCapability>>(
    taskType: string,
  ): Promise<ApiResponse<T>> {
    const { data } = await apiClient.get('/content/provider-capabilities', {
      params: { task_type: taskType },
    });
    return data;
  },
};

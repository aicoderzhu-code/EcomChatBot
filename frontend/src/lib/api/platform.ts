import apiClient from './client';
import { ApiResponse } from '@/types';

export interface PlatformConfig {
  id: number;
  tenant_id: string;
  platform_type: string;
  app_key: string;
  shop_id: string | null;
  shop_name: string | null;
  is_active: boolean;
  auto_reply_threshold: number;
  human_takeover_message: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformConfigUpdate {
  app_key: string;
  app_secret: string;
  auto_reply_threshold: number;
  human_takeover_message?: string | null;
}

export const platformApi = {
  getConfigs: async (): Promise<ApiResponse<PlatformConfig[]>> => {
    const response = await apiClient.get<ApiResponse<PlatformConfig[]>>('/platform/config');
    return response.data;
  },

  upsertConfig: async (
    platform: string,
    data: PlatformConfigUpdate,
    configId?: number
  ): Promise<ApiResponse<PlatformConfig>> => {
    const url = configId
      ? `/platform/config?platform=${platform}&config_id=${configId}`
      : `/platform/config?platform=${platform}`;
    const response = await apiClient.put<ApiResponse<PlatformConfig>>(url, data);
    return response.data;
  },

  disconnect: async (configId: number): Promise<ApiResponse<{ message: string }>> => {
    const response = await apiClient.delete<ApiResponse<{ message: string }>>(
      `/platform/config/${configId}`
    );
    return response.data;
  },

  getAuthUrl: (configId: number, redirectUri: string): string => {
    return `/api/v1/platform/pinduoduo/auth?config_id=${configId}&redirect_uri=${encodeURIComponent(redirectUri)}`;
  },

  getDouyinAuthUrl: (configId: number, redirectUri: string): string => {
    return `/api/v1/platform/douyin/auth?config_id=${configId}&redirect_uri=${encodeURIComponent(redirectUri)}`;
  },

  sendPlatformMessage: async (
    conversationId: string,
    content: string
  ): Promise<ApiResponse<{ success: boolean }>> => {
    const response = await apiClient.post<ApiResponse<{ success: boolean }>>(
      '/platform/pinduoduo/reply',
      { conversation_id: conversationId, content }
    );
    return response.data;
  },

  sendDouyinMessage: async (
    conversationId: string,
    content: string
  ): Promise<ApiResponse<{ success: boolean }>> => {
    const response = await apiClient.post<ApiResponse<{ success: boolean }>>(
      '/platform/douyin/reply',
      { conversation_id: conversationId, content }
    );
    return response.data;
  },
};

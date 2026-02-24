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
    data: PlatformConfigUpdate
  ): Promise<ApiResponse<PlatformConfig>> => {
    const response = await apiClient.put<ApiResponse<PlatformConfig>>(
      `/platform/config?platform=${platform}`,
      data
    );
    return response.data;
  },

  disconnect: async (platform: string): Promise<ApiResponse<{ message: string }>> => {
    const response = await apiClient.delete<ApiResponse<{ message: string }>>(
      `/platform/config/${platform}`
    );
    return response.data;
  },

  getAuthUrl: (appKey: string, redirectUri: string): string => {
    return `/api/v1/platform/pinduoduo/auth?app_key=${encodeURIComponent(appKey)}&redirect_uri=${encodeURIComponent(redirectUri)}`;
  },
};

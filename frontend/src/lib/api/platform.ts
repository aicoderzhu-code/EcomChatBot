import apiClient from './client';
import type { ApiResponse, PlatformApp, PlatformConfig as PlatformConfigType, EcommercePlatform } from '@/types';

// 保留旧接口兼容
export interface PlatformConfigLegacy {
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

// 向后兼容别名
export type PlatformConfig = PlatformConfigLegacy;

export interface PlatformConfigUpdate {
  app_key: string;
  app_secret: string;
  auto_reply_threshold: number;
  human_takeover_message?: string | null;
}

export const platformApi = {
  // ===== 新 ISV 模式 API =====

  // 获取可用的 ISV 应用
  getApps: async (): Promise<PlatformApp[]> => {
    const response = await apiClient.get<PlatformApp[]>('/platform/apps');
    return response.data;
  },

  // 获取租户的所有平台配置（新版，含授权状态）
  getPlatformConfigs: async (): Promise<PlatformConfigType[]> => {
    const response = await apiClient.get<PlatformConfigType[]>('/platform/configs');
    return response.data;
  },

  // 发起 OAuth 授权（通用）
  getOAuthUrl: (platformType: EcommercePlatform, redirectUri: string, configId?: number): string => {
    const params = new URLSearchParams({ redirect_uri: redirectUri });
    if (configId) params.set('config_id', String(configId));
    return `/api/v1/platform/${platformType}/auth?${params}`;
  },

  // 断开平台连接（新版）
  disconnectPlatform: async (configId: number): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.delete<{ success: boolean; message: string }>(
      `/platform/configs/${configId}`
    );
    return response.data;
  },

  // 通用人工回复
  sendReply: async (
    platformType: EcommercePlatform,
    conversationId: string,
    content: string,
  ): Promise<{ success: boolean }> => {
    const response = await apiClient.post<{ success: boolean }>(
      `/platform/${platformType}/reply`,
      { conversation_id: conversationId, content }
    );
    return response.data;
  },

  // ===== 旧 API（向后兼容） =====

  getConfigs: async (): Promise<ApiResponse<PlatformConfigLegacy[]>> => {
    const response = await apiClient.get<ApiResponse<PlatformConfigLegacy[]>>('/platform/config');
    return response.data;
  },

  upsertConfig: async (
    platform: string,
    data: PlatformConfigUpdate,
    configId?: number
  ): Promise<ApiResponse<PlatformConfigLegacy>> => {
    const url = configId
      ? `/platform/config?platform=${platform}&config_id=${configId}`
      : `/platform/config?platform=${platform}`;
    const response = await apiClient.put<ApiResponse<PlatformConfigLegacy>>(url, data);
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

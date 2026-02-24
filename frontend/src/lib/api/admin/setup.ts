import adminApiClient from './client';
import { ApiResponse } from '@/types';
import { SetupStatus, InitialAdminCreate, InitialAdminResponse } from '@/types/admin';

export const setupApi = {
  /**
   * 获取系统初始化状态
   * 无需认证，用于检查系统是否需要初始化
   */
  getStatus: async (): Promise<ApiResponse<SetupStatus>> => {
    const response = await adminApiClient.get<ApiResponse<SetupStatus>>(
      '/setup/status'
    );
    return response.data;
  },

  /**
   * 创建初始超级管理员
   * 仅当系统未初始化时可用
   */
  initialize: async (data: InitialAdminCreate): Promise<ApiResponse<InitialAdminResponse>> => {
    const response = await adminApiClient.post<ApiResponse<InitialAdminResponse>>(
      '/setup/init',
      data
    );
    return response.data;
  },
};

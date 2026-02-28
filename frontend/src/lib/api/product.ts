import apiClient from './client';
import type { ApiResponse, PaginatedResponse, Product, SyncTask, SyncSchedule } from '@/types';

export const productApi = {
  // ===== 商品 =====

  async listProducts(params?: {
    keyword?: string;
    category?: string;
    status?: string;
    platform_config_id?: number;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<Product>>> {
    const { data } = await apiClient.get('/products', { params });
    return data;
  },

  async getProduct(productId: number): Promise<ApiResponse<Product>> {
    const { data } = await apiClient.get(`/products/${productId}`);
    return data;
  },

  // ===== 同步 =====

  async triggerSync(platformConfigId: number, syncType: 'full' | 'incremental' = 'full'): Promise<ApiResponse<SyncTask>> {
    const { data } = await apiClient.post('/products/sync', {
      platform_config_id: platformConfigId,
      sync_type: syncType,
    });
    return data;
  },

  async listSyncTasks(params?: {
    platform_config_id?: number;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<SyncTask>>> {
    const { data } = await apiClient.get('/products/sync/tasks', { params });
    return data;
  },

  // ===== 同步调度 =====

  async getSyncSchedule(platformConfigId: number): Promise<ApiResponse<SyncSchedule | null>> {
    const { data } = await apiClient.get(`/products/sync/schedule/${platformConfigId}`);
    return data;
  },

  async updateSyncSchedule(
    platformConfigId: number,
    params: { interval_minutes?: number; is_active?: boolean }
  ): Promise<ApiResponse<SyncSchedule>> {
    const { data } = await apiClient.put(`/products/sync/schedule/${platformConfigId}`, params);
    return data;
  },
};

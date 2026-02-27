import adminApiClient from './client';
import { ApiResponse } from '@/types';
import {
  TenantInfo,
  TenantWithAPIKey,
  TenantCreateRequest,
  TenantUpdateStatusRequest,
  TenantQueryParams,
  BatchOperationRequest,
  BatchOperationResponse,
  OverdueTenantListResponse,
  AdminPaginatedResponse,
  TenantUsageDetail,
} from '@/types/admin';

export const adminTenantsApi = {
  // Get tenant list
  list: async (params?: TenantQueryParams): Promise<ApiResponse<AdminPaginatedResponse<TenantInfo>>> => {
    const response = await adminApiClient.get<ApiResponse<AdminPaginatedResponse<TenantInfo>>>(
      '/admin/tenants',
      { params }
    );
    return response.data;
  },

  // Get tenant detail
  get: async (tenantId: string): Promise<ApiResponse<TenantInfo>> => {
    const response = await adminApiClient.get<ApiResponse<TenantInfo>>(
      `/admin/tenants/${tenantId}`
    );
    return response.data;
  },

  // Create tenant
  create: async (data: TenantCreateRequest): Promise<ApiResponse<TenantWithAPIKey>> => {
    const response = await adminApiClient.post<ApiResponse<TenantWithAPIKey>>(
      '/admin/tenants',
      data
    );
    return response.data;
  },

  // Update tenant status
  updateStatus: async (
    tenantId: string,
    data: TenantUpdateStatusRequest
  ): Promise<ApiResponse<TenantInfo>> => {
    const response = await adminApiClient.put<ApiResponse<TenantInfo>>(
      `/admin/tenants/${tenantId}/status`,
      data
    );
    return response.data;
  },

  // Assign plan to tenant
  assignPlan: async (
    tenantId: string,
    planType: string,
    durationMonths: number = 1
  ): Promise<ApiResponse<{ subscription_id: string }>> => {
    const response = await adminApiClient.post<ApiResponse<{ subscription_id: string }>>(
      `/admin/tenants/${tenantId}/assign-plan`,
      null,
      { params: { plan_type: planType, duration_months: durationMonths } }
    );
    return response.data;
  },

  // Adjust quota
  adjustQuota: async (
    tenantId: string,
    quotaType: string,
    amount: number,
    reason?: string
  ): Promise<ApiResponse<Record<string, unknown>>> => {
    const response = await adminApiClient.post<ApiResponse<Record<string, unknown>>>(
      `/admin/tenants/${tenantId}/adjust-quota`,
      null,
      { params: { quota_type: quotaType, amount, reason } }
    );
    return response.data;
  },

  // Batch operation
  batchOperation: async (data: BatchOperationRequest): Promise<ApiResponse<BatchOperationResponse>> => {
    const response = await adminApiClient.post<ApiResponse<BatchOperationResponse>>(
      '/admin/tenants/batch-operation',
      data
    );
    return response.data;
  },

  // Get overdue tenants
  getOverdue: async (
    page: number = 1,
    pageSize: number = 20,
    minDaysOverdue: number = 0
  ): Promise<ApiResponse<OverdueTenantListResponse>> => {
    const response = await adminApiClient.get<ApiResponse<OverdueTenantListResponse>>(
      '/admin/tenants/overdue',
      { params: { page, page_size: pageSize, min_days_overdue: minDaysOverdue } }
    );
    return response.data;
  },

  // Send payment reminder
  sendReminder: async (tenantId: string): Promise<ApiResponse<{ message: string }>> => {
    const response = await adminApiClient.post<ApiResponse<{ message: string }>>(
      `/admin/tenants/${tenantId}/send-reminder`
    );
    return response.data;
  },

  // Reset API key
  resetApiKey: async (tenantId: string): Promise<ApiResponse<{ api_key: string; message: string }>> => {
    const response = await adminApiClient.post<ApiResponse<{ api_key: string; message: string }>>(
      `/admin/tenants/${tenantId}/reset-api-key`
    );
    return response.data;
  },

  // Get tenant usage statistics
  getUsage: async (tenantId: string, year?: number, month?: number): Promise<ApiResponse<TenantUsageDetail>> => {
    const response = await adminApiClient.get<ApiResponse<TenantUsageDetail>>(
      `/admin/tenants/${tenantId}/usage`,
      { params: { year, month } }
    );
    return response.data;
  },
};

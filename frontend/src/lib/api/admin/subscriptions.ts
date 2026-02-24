import adminApiClient from './client';
import { ApiResponse, PaginatedResponse } from '@/types';
import { SubscriptionInfo } from '@/types/admin';

interface ListSubscriptionsParams {
  page?: number;
  size?: number;
  status?: string;
  plan_type?: string;
  tenant_id?: string;
}

interface AssignPlanParams {
  plan_type: string;
  days?: number;
}

interface SubscriptionPlan {
  name: string;
  price: number;
  days: number;
}

export const adminSubscriptionsApi = {
  list: async (params: ListSubscriptionsParams): Promise<ApiResponse<PaginatedResponse<SubscriptionInfo>>> => {
    const response = await adminApiClient.get<ApiResponse<PaginatedResponse<SubscriptionInfo>>>(
      '/subscriptions',
      { params }
    );
    return response.data;
  },

  assignPlan: async (tenantId: string, data: AssignPlanParams): Promise<ApiResponse<SubscriptionInfo>> => {
    const response = await adminApiClient.post<ApiResponse<SubscriptionInfo>>(
      `/tenants/${tenantId}/assign-plan`,
      data
    );
    return response.data;
  },

  getPlans: async (): Promise<ApiResponse<{ plans: Record<string, SubscriptionPlan> }>> => {
    const response = await adminApiClient.get<ApiResponse<{ plans: Record<string, SubscriptionPlan> }>>(
      '/subscriptions/plans'
    );
    return response.data;
  },

  getTenantSubscription: async (tenantId: string): Promise<ApiResponse<SubscriptionInfo>> => {
    const response = await adminApiClient.get<ApiResponse<SubscriptionInfo>>(
      `/tenants/${tenantId}/subscription`
    );
    return response.data;
  },
};

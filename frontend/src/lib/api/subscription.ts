import apiClient from './client';
import { ApiResponse } from '@/types';

export interface SubscriptionStatus {
  subscription_id: string;
  plan_type: string;
  plan_name: string;
  status: 'active' | 'grace' | 'expired';
  expire_at: string | null;
  grace_period_end: string | null;
  is_in_grace: boolean;
  is_trial: boolean;
}

export interface SubscriptionPlan {
  name: string;
  price: number;
  days: number;
}

export const subscriptionApi = {
  getStatus: async (): Promise<ApiResponse<SubscriptionStatus>> => {
    const response = await apiClient.get<ApiResponse<SubscriptionStatus>>(
      '/tenant/subscription/status'
    );
    return response.data;
  },
};

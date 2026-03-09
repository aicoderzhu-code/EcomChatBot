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

export interface CreateOrderResponse {
  order_id: number;
  order_number: string;
  amount: number;
  currency: string;
  qr_code_url: string;
  expires_at: string;
}

export interface OrderStatus {
  order_number: string;
  status: 'pending' | 'paid' | 'failed' | 'cancelled' | 'expired';
  amount: number;
  trade_no: string | null;
  qr_code_url: string | null;
  paid_at: string | null;
  expired_at: string;
  created_at: string;
}

export interface QuotaUsage {
  billing_period: string;
  reply_quota: number;
  reply_used: number;
  image_gen_quota: number;
  image_gen_used: number;
  video_gen_quota: number;
  video_gen_used: number;
}

export const subscriptionApi = {
  getStatus: async (): Promise<ApiResponse<SubscriptionStatus>> => {
    const response = await apiClient.get<ApiResponse<SubscriptionStatus>>(
      '/tenant/subscription/status'
    );
    return response.data;
  },

  createOrder: async (params: {
    plan_type: string;
    subscription_type?: string;
    payment_channel?: string;
  }): Promise<ApiResponse<CreateOrderResponse>> => {
    const response = await apiClient.post<ApiResponse<CreateOrderResponse>>(
      '/payment/orders/create',
      params
    );
    return response.data;
  },

  syncOrder: async (orderNumber: string): Promise<ApiResponse<{ order: OrderStatus }>> => {
    const response = await apiClient.post<ApiResponse<{ order: OrderStatus }>>(
      `/payment/orders/${orderNumber}/sync`
    );
    return response.data;
  },

  getQuotaUsage: async (): Promise<ApiResponse<QuotaUsage>> => {
    const response = await apiClient.get<ApiResponse<QuotaUsage>>(
      '/quota/usage'
    );
    return response.data;
  },
};

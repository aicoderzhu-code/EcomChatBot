import apiClient from './client';
import type { ApiResponse, PaginatedResponse } from '@/types';

// ===== 订单类型 =====

export interface OrderItem {
  id: number;
  tenant_id: string;
  platform_config_id: number;
  platform_order_id: string;
  product_id: number | null;
  product_title: string;
  buyer_id: string;
  quantity: number;
  unit_price: number;
  total_amount: number;
  status: 'pending' | 'paid' | 'shipped' | 'completed' | 'refunded' | 'cancelled';
  paid_at: string | null;
  shipped_at: string | null;
  completed_at: string | null;
  refund_amount: number | null;
  platform_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface OrderOverview {
  total_orders: number;
  total_revenue: number;
  avg_order_value: number;
  total_items: number;
  status_distribution: Record<string, number>;
  daily_trend: Array<{ date: string; orders: number; revenue: number }>;
  refund_count: number;
  refund_total: number;
}

export interface TopProduct {
  product_title: string;
  order_count: number;
  total_revenue: number;
  total_quantity: number;
}

export interface BuyerStat {
  buyer_id: string;
  order_count: number;
  total_spent: number;
}

// ===== 分析报告类型 =====

export interface AnalysisReport {
  id: number;
  tenant_id: string;
  report_type: 'daily' | 'weekly' | 'monthly' | 'custom';
  title: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  period_start: string | null;
  period_end: string | null;
  summary: string | null;
  statistics: Record<string, unknown> | null;
  charts_data: Record<string, unknown> | null;
  file_url: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// ===== API 函数 =====

export const analyticsApi = {
  // ===== 订单 =====

  async listOrders(params?: {
    status?: string;
    platform_config_id?: number;
    keyword?: string;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<OrderItem>>> {
    const { data } = await apiClient.get('/orders', { params });
    return data;
  },

  async getOrder(orderId: number): Promise<ApiResponse<OrderItem>> {
    const { data } = await apiClient.get(`/orders/${orderId}`);
    return data;
  },

  async triggerOrderSync(platformConfigId: number): Promise<ApiResponse<unknown>> {
    const { data } = await apiClient.post('/orders/sync', {
      platform_config_id: platformConfigId,
    });
    return data;
  },

  // ===== 订单分析 =====

  async getOrderOverview(days: number = 30): Promise<ApiResponse<OrderOverview>> {
    const { data } = await apiClient.get('/orders/analytics/overview', {
      params: { days },
    });
    return data;
  },

  async getTopProducts(days: number = 30, limit: number = 10): Promise<ApiResponse<TopProduct[]>> {
    const { data } = await apiClient.get('/orders/analytics/top-products', {
      params: { days, limit },
    });
    return data;
  },

  async getBuyerStats(days: number = 30, limit: number = 10): Promise<ApiResponse<BuyerStat[]>> {
    const { data } = await apiClient.get('/orders/analytics/buyer-stats', {
      params: { days, limit },
    });
    return data;
  },

  // ===== 分析报告 =====

  async listReports(params?: {
    report_type?: string;
    status?: string;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<AnalysisReport>>> {
    const { data } = await apiClient.get('/reports', { params });
    return data;
  },

  async getReport(reportId: number): Promise<ApiResponse<AnalysisReport>> {
    const { data } = await apiClient.get(`/reports/${reportId}`);
    return data;
  },

  async createReport(body: {
    report_type: string;
    title: string;
    period_start?: string;
    period_end?: string;
  }): Promise<ApiResponse<AnalysisReport>> {
    const { data } = await apiClient.post('/reports', body);
    return data;
  },

  async generateReport(reportId: number): Promise<ApiResponse<AnalysisReport>> {
    const { data } = await apiClient.post(`/reports/${reportId}/generate`);
    return data;
  },

  async deleteReport(reportId: number): Promise<ApiResponse<null>> {
    const { data } = await apiClient.delete(`/reports/${reportId}`);
    return data;
  },
};

import apiClient from './client';
import type { ApiResponse, PaginatedResponse } from '@/types';

// ===== 定价相关类型 =====

export interface CompetitorProduct {
  id: number;
  tenant_id: string;
  product_id: number;
  competitor_name: string;
  competitor_platform: string | null;
  competitor_url: string | null;
  competitor_price: number;
  competitor_sales: number;
  last_checked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PricingAnalysis {
  id: number;
  tenant_id: string;
  product_id: number;
  current_price: number;
  suggested_price: number;
  min_price: number | null;
  max_price: number | null;
  strategy: string;
  competitor_count: number;
  competitor_avg_price: number | null;
  analysis_summary: string | null;
  analysis_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// ===== API 函数 =====

export const pricingApi = {
  // ===== 竞品管理 =====

  async addCompetitor(body: {
    product_id: number;
    competitor_name: string;
    competitor_platform?: string;
    competitor_url?: string;
    competitor_price: number;
    competitor_sales?: number;
  }): Promise<ApiResponse<CompetitorProduct>> {
    const { data } = await apiClient.post('/pricing/competitors', body);
    return data;
  },

  async listCompetitors(
    productId: number,
    params?: { page?: number; size?: number }
  ): Promise<ApiResponse<PaginatedResponse<CompetitorProduct>>> {
    const { data } = await apiClient.get(`/pricing/competitors/${productId}`, {
      params,
    });
    return data;
  },

  async deleteCompetitor(
    competitorId: number
  ): Promise<ApiResponse<null>> {
    const { data } = await apiClient.delete(
      `/pricing/competitors/${competitorId}`
    );
    return data;
  },

  // ===== 定价分析 =====

  async analyzePricing(body: {
    product_id: number;
    strategy?: string;
  }): Promise<ApiResponse<PricingAnalysis>> {
    const { data } = await apiClient.post('/pricing/analyze', body);
    return data;
  },

  async getLatestAnalysis(
    productId: number
  ): Promise<ApiResponse<PricingAnalysis>> {
    const { data } = await apiClient.get(`/pricing/analysis/${productId}`);
    return data;
  },

  async listAnalysisHistory(
    productId: number,
    params?: { page?: number; size?: number }
  ): Promise<ApiResponse<PaginatedResponse<PricingAnalysis>>> {
    const { data } = await apiClient.get(
      `/pricing/analysis/${productId}/history`,
      { params }
    );
    return data;
  },
};

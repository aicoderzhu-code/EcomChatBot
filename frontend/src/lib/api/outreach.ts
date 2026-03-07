import apiClient from './client';
import type {
  ApiResponse,
  PaginatedResponse,
  CustomerSegment,
  SegmentMember,
  OutreachCampaign,
  CampaignStats,
  OutreachTask,
  OutreachRule,
  FollowUpPlan,
  FollowUpDashboard,
  RecommendationRule,
  RecommendationLog,
  RecommendationStats,
} from '@/types';

// ===== 客户分群 =====

export const segmentApi = {
  async list(params?: { page?: number; size?: number }): Promise<ApiResponse<PaginatedResponse<CustomerSegment>>> {
    const { data } = await apiClient.get('/segments', { params });
    return data;
  },

  async get(id: number): Promise<ApiResponse<CustomerSegment>> {
    const { data } = await apiClient.get(`/segments/${id}`);
    return data;
  },

  async create(payload: {
    name: string;
    description?: string;
    segment_type?: string;
    filter_rules?: Record<string, unknown>;
  }): Promise<ApiResponse<CustomerSegment>> {
    const { data } = await apiClient.post('/segments', payload);
    return data;
  },

  async update(id: number, payload: Record<string, unknown>): Promise<ApiResponse<CustomerSegment>> {
    const { data } = await apiClient.put(`/segments/${id}`, payload);
    return data;
  },

  async delete(id: number): Promise<ApiResponse<unknown>> {
    const { data } = await apiClient.delete(`/segments/${id}`);
    return data;
  },

  async refresh(id: number): Promise<ApiResponse<CustomerSegment>> {
    const { data } = await apiClient.post(`/segments/${id}/refresh`);
    return data;
  },

  async getMembers(id: number, params?: { page?: number; size?: number }): Promise<ApiResponse<PaginatedResponse<SegmentMember>>> {
    const { data } = await apiClient.get(`/segments/${id}/members`, { params });
    return data;
  },

  async addMembers(id: number, userIds: number[]): Promise<ApiResponse<{ added: number }>> {
    const { data } = await apiClient.post(`/segments/${id}/members`, { user_ids: userIds });
    return data;
  },

  async preview(filterRules: Record<string, unknown>): Promise<ApiResponse<{ matched_count: number; sample_users: unknown[] }>> {
    const { data } = await apiClient.post('/segments/preview', { filter_rules: filterRules });
    return data;
  },
};

// ===== 外呼活动 =====

export const campaignApi = {
  async list(params?: { status?: string; page?: number; size?: number }): Promise<ApiResponse<PaginatedResponse<OutreachCampaign>>> {
    const { data } = await apiClient.get('/outreach/campaigns', { params });
    return data;
  },

  async get(id: number): Promise<ApiResponse<OutreachCampaign>> {
    const { data } = await apiClient.get(`/outreach/campaigns/${id}`);
    return data;
  },

  async create(payload: Record<string, unknown>): Promise<ApiResponse<OutreachCampaign>> {
    const { data } = await apiClient.post('/outreach/campaigns', payload);
    return data;
  },

  async update(id: number, payload: Record<string, unknown>): Promise<ApiResponse<OutreachCampaign>> {
    const { data } = await apiClient.put(`/outreach/campaigns/${id}`, payload);
    return data;
  },

  async launch(id: number): Promise<ApiResponse<OutreachCampaign>> {
    const { data } = await apiClient.post(`/outreach/campaigns/${id}/launch`);
    return data;
  },

  async pause(id: number): Promise<ApiResponse<OutreachCampaign>> {
    const { data } = await apiClient.post(`/outreach/campaigns/${id}/pause`);
    return data;
  },

  async resume(id: number): Promise<ApiResponse<OutreachCampaign>> {
    const { data } = await apiClient.post(`/outreach/campaigns/${id}/resume`);
    return data;
  },

  async cancel(id: number): Promise<ApiResponse<OutreachCampaign>> {
    const { data } = await apiClient.post(`/outreach/campaigns/${id}/cancel`);
    return data;
  },

  async getTasks(id: number, params?: { status?: string; page?: number; size?: number }): Promise<ApiResponse<PaginatedResponse<OutreachTask>>> {
    const { data } = await apiClient.get(`/outreach/campaigns/${id}/tasks`, { params });
    return data;
  },

  async getStats(id: number): Promise<ApiResponse<CampaignStats>> {
    const { data } = await apiClient.get(`/outreach/campaigns/${id}/stats`);
    return data;
  },
};

// ===== 自动规则 =====

export const ruleApi = {
  async list(params?: { page?: number; size?: number }): Promise<ApiResponse<PaginatedResponse<OutreachRule>>> {
    const { data } = await apiClient.get('/outreach/rules', { params });
    return data;
  },

  async get(id: number): Promise<ApiResponse<OutreachRule>> {
    const { data } = await apiClient.get(`/outreach/rules/${id}`);
    return data;
  },

  async create(payload: Record<string, unknown>): Promise<ApiResponse<OutreachRule>> {
    const { data } = await apiClient.post('/outreach/rules', payload);
    return data;
  },

  async update(id: number, payload: Record<string, unknown>): Promise<ApiResponse<OutreachRule>> {
    const { data } = await apiClient.put(`/outreach/rules/${id}`, payload);
    return data;
  },

  async delete(id: number): Promise<ApiResponse<unknown>> {
    const { data } = await apiClient.delete(`/outreach/rules/${id}`);
    return data;
  },

  async toggle(id: number): Promise<ApiResponse<OutreachRule>> {
    const { data } = await apiClient.post(`/outreach/rules/${id}/toggle`);
    return data;
  },

  async getStats(id: number): Promise<ApiResponse<{ total_triggered: number; total_converted: number; conversion_rate: number }>> {
    const { data } = await apiClient.get(`/outreach/rules/${id}/stats`);
    return data;
  },
};

// ===== 定时跟进 =====

export const followUpApi = {
  async listPlans(params?: { status?: string; page?: number; size?: number }): Promise<ApiResponse<PaginatedResponse<FollowUpPlan>>> {
    const { data } = await apiClient.get('/follow-up/plans', { params });
    return data;
  },

  async getPlan(id: number): Promise<ApiResponse<FollowUpPlan>> {
    const { data } = await apiClient.get(`/follow-up/plans/${id}`);
    return data;
  },

  async createPlan(payload: Record<string, unknown>): Promise<ApiResponse<FollowUpPlan>> {
    const { data } = await apiClient.post('/follow-up/plans', payload);
    return data;
  },

  async updatePlan(id: number, payload: Record<string, unknown>): Promise<ApiResponse<FollowUpPlan>> {
    const { data } = await apiClient.put(`/follow-up/plans/${id}`, payload);
    return data;
  },

  async cancelPlan(id: number): Promise<ApiResponse<FollowUpPlan>> {
    const { data } = await apiClient.post(`/follow-up/plans/${id}/cancel`);
    return data;
  },

  async executePlan(id: number): Promise<ApiResponse<{ executed: boolean }>> {
    const { data } = await apiClient.post(`/follow-up/plans/${id}/execute`);
    return data;
  },

  async getDashboard(): Promise<ApiResponse<FollowUpDashboard>> {
    const { data } = await apiClient.get('/follow-up/dashboard');
    return data;
  },
};

// ===== 增购推荐 =====

export const recommendationApi = {
  async listRules(params?: { page?: number; size?: number }): Promise<ApiResponse<PaginatedResponse<RecommendationRule>>> {
    const { data } = await apiClient.get('/recommendations/rules', { params });
    return data;
  },

  async getRule(id: number): Promise<ApiResponse<RecommendationRule>> {
    const { data } = await apiClient.get(`/recommendations/rules/${id}`);
    return data;
  },

  async createRule(payload: Record<string, unknown>): Promise<ApiResponse<RecommendationRule>> {
    const { data } = await apiClient.post('/recommendations/rules', payload);
    return data;
  },

  async updateRule(id: number, payload: Record<string, unknown>): Promise<ApiResponse<RecommendationRule>> {
    const { data } = await apiClient.put(`/recommendations/rules/${id}`, payload);
    return data;
  },

  async deleteRule(id: number): Promise<ApiResponse<unknown>> {
    const { data } = await apiClient.delete(`/recommendations/rules/${id}`);
    return data;
  },

  async listLogs(params?: {
    user_id?: number;
    order_id?: number;
    conversation_id?: string;
    page?: number;
    size?: number;
  }): Promise<ApiResponse<PaginatedResponse<RecommendationLog>>> {
    const { data } = await apiClient.get('/recommendations/logs', { params });
    return data;
  },

  async getStats(): Promise<ApiResponse<RecommendationStats>> {
    const { data } = await apiClient.get('/recommendations/stats');
    return data;
  },

  async preview(payload: { rule_id?: number; user_id?: number; product_id?: number }): Promise<ApiResponse<unknown>> {
    const { data } = await apiClient.post('/recommendations/preview', payload);
    return data;
  },
};

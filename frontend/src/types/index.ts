// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: { code: string; message: string } | null;
  meta?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Auth Types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  tenant_id: string;
}

export interface RegisterRequest {
  company_name: string;
  contact_name: string;
  contact_email: string;
  contact_phone?: string;
  password: string;
}

export interface RegisterResponse {
  tenant_id: string;
  api_key: string;
  message: string;
}

export interface TokenRefreshRequest {
  refresh_token: string;
}

export interface TokenRefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// User Types
export interface User {
  id: number;
  user_external_id: string;
  name: string | null;
  level: string | null;
  region: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
}

export interface Tenant {
  id: number;
  tenant_id: string;
  company_name: string;
  contact_name: string | null;
  contact_email: string;
  status: string;
  current_plan: string;
}

// Conversation Types
export interface Conversation {
  id: number;
  conversation_id: string;
  user_external_id: string;
  channel: string;
  status: 'active' | 'waiting' | 'closed';
  started_at: string;
  ended_at: string | null;
  message_count: number;
  last_message_at: string | null;
  last_message_preview: string | null;
  satisfaction_score: number | null;
  platform_type: string | null;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
  user: User;
}

export interface Message {
  id: number;
  message_id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  input_tokens: number;
  output_tokens: number;
  isStreaming?: boolean;
}

export interface ConversationCreateRequest {
  user_id: string;
  channel: string;
  metadata?: Record<string, unknown>;
}

export interface MessageCreateRequest {
  content: string;
}

// Knowledge Types
export interface KnowledgeDocument {
  id: number;
  knowledge_id: string;
  title: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  uploaded_at: string;
}

export interface KnowledgeSearchResult {
  knowledge_id: string;
  title: string;
  content: string;
  score: number;
  source: string;
}

export interface DashboardStats {
  today_conversations: number;
  today_conversations_change: number;
  active_users: number;
  active_users_change: number;
  token_usage: number;
  token_remaining: number;
}

export interface TrendData {
  date: string;
  value: number;
}

export interface IntentDistribution {
  intent: string;
  count: number;
}

// WebSocket Types
export interface WSMessage {
  type: 'message' | 'stream' | 'system' | 'error' | 'metadata' | 'pong';
  role?: 'user' | 'assistant';
  content?: string;
  chunk?: string;
  is_final?: boolean;
  timestamp?: string;
  tokens?: {
    input: number;
    output: number;
    total: number;
  };
  model?: string;
  used_rag?: boolean;
  sources?: Array<{
    knowledge_id: string;
    title: string;
    score: number;
  }>;
  error_code?: string;
}

export interface WSSendMessage {
  type: 'message' | 'ping';
  content?: string;
  use_rag?: boolean;
}

// ===== 商品管理 =====

export interface Product {
  id: number;
  tenant_id: string;
  platform_config_id: number;
  platform_product_id: string;
  title: string;
  description: string | null;
  price: number;
  original_price: number | null;
  currency: string;
  category: string | null;
  images: string[] | null;
  videos: string[] | null;
  attributes: Record<string, unknown> | null;
  sales_count: number;
  stock: number;
  status: 'active' | 'inactive' | 'deleted';
  knowledge_base_id: number | null;
  last_synced_at: string | null;
  platform_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface SyncTask {
  id: number;
  tenant_id: string;
  platform_config_id: number;
  sync_target: 'product' | 'order';
  sync_type: 'full' | 'incremental';
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_count: number;
  synced_count: number;
  failed_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SyncSchedule {
  id: number;
  tenant_id: string;
  platform_config_id: number;
  interval_minutes: number;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
  updated_at: string;
}

// 平台类型
export type EcommercePlatform = 'pinduoduo' | 'douyin' | 'taobao' | 'jd' | 'kuaishou';

// 授权状态
export type AuthorizationStatus = 'pending' | 'authorized' | 'expired' | 'revoked';

// ISV 应用
export interface PlatformApp {
  platform_type: EcommercePlatform;
  app_name: string;
  status: string;
}

// 平台配置（扩展）
export interface PlatformConfig {
  id: number;
  tenant_id: string;
  platform_type: EcommercePlatform;
  app_key: string;
  shop_id: string | null;
  shop_name: string | null;
  is_active: boolean;
  authorization_status: AuthorizationStatus;
  auto_reply_threshold: number;
  human_takeover_message: string | null;
  expires_at: string | null;
  token_expires_at: string | null;
  refresh_expires_at: string | null;
  last_token_refresh: string | null;
  scopes: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// 售后记录
export interface AfterSaleRecord {
  id: number;
  platform_config_id: number;
  platform_aftersale_id: string;
  order_id: number | null;
  aftersale_type: 'refund_only' | 'return_refund' | 'exchange';
  status: string;
  reason: string | null;
  refund_amount: number;
  buyer_id: string | null;
  created_at: string;
}

// ===== 内容生成 =====

export type SceneType =
  | 'main_image'
  | 'detail_image'
  | 'promo_poster'
  | 'main_video'
  | 'short_video'
  | 'detail_video';

export type GenerationMode = 'simple' | 'advanced';

export type ReviewStatus = 'pending' | 'approved' | 'rejected';

export interface ContentTemplate {
  id: number;
  tenant_id: string | null;
  name: string;
  category: 'poster' | 'video';
  scene_type: SceneType;
  prompt_template: string;
  variables: TemplateVariable[] | null;
  style_options: string[] | null;
  platform_presets: Record<string, { size: string }> | null;
  default_params: Record<string, unknown> | null;
  thumbnail_url: string | null;
  is_system: boolean;
  is_active: boolean;
  sort_order: number;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface TemplateVariable {
  key: string;
  label: string;
  source: string;
  required: boolean;
  default?: string;
}

export interface PlatformMediaSpec {
  id: number;
  platform_type: string;
  media_type: string;
  spec_name: string;
  width: number;
  height: number;
  max_file_size: number | null;
  format: string | null;
  duration_range: { min: number; max: number } | null;
  extra_rules: Record<string, unknown> | null;
}

export interface TemplateRenderRequest {
  product_id?: number;
  overrides?: Record<string, string>;
  target_platform?: string;
}

export interface TemplateRenderResponse {
  rendered_prompt: string;
  resolved_params: Record<string, unknown>;
  variables_used: Record<string, string>;
}

export interface GenerationTask {
  id: number;
  tenant_id: string;
  product_id: number | null;
  task_type: 'poster' | 'video' | 'title' | 'description';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  prompt: string;
  model_config_id: number | null;
  prompt_id: number | null;
  params: Record<string, unknown> | null;
  result_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  template_id: number | null;
  scene_type: SceneType | null;
  target_platform: string | null;
  generation_mode: GenerationMode;
  created_at: string;
  updated_at: string;
}

export interface GeneratedAsset {
  id: number;
  tenant_id: string;
  task_id: number;
  product_id: number | null;
  asset_type: 'image' | 'video' | 'text';
  file_url: string | null;
  content: string | null;
  thumbnail_url: string | null;
  metadata: Record<string, unknown> | null;
  platform_url: string | null;
  is_selected: boolean;
  scene_type: SceneType | null;
  target_platform: string | null;
  review_status: ReviewStatus;
  created_at: string;
  updated_at: string;
}

export interface GenerateRequest {
  product_id?: number;
  task_type: 'poster' | 'video' | 'title' | 'description';
  prompt: string;
  prompt_id?: number;
  model_config_id?: number;
  params?: Record<string, unknown>;
  template_id?: number;
  scene_type?: SceneType;
  target_platform?: string;
  generation_mode?: GenerationMode;
}

export interface BatchGenerateRequest {
  template_id: number;
  product_ids: number[];
  target_platform?: string;
  params?: Record<string, unknown>;
}

export interface ReviewAssetRequest {
  review_status: 'approved' | 'rejected';
  note?: string;
}

export interface BatchUploadAssetsRequest {
  asset_ids: number[];
  platform_config_id: number;
}

// ===== 智能触达 =====

// 客户分群
export type SegmentType = 'manual' | 'dynamic';

export interface CustomerSegment {
  id: number;
  tenant_id: string;
  name: string;
  description: string | null;
  segment_type: SegmentType;
  filter_rules: Record<string, unknown> | null;
  member_count: number;
  last_refreshed_at: string | null;
  is_active: number;
  created_at: string;
  updated_at: string;
}

export interface SegmentMember {
  id: number;
  user_id: number;
  nickname: string | null;
  vip_level: number;
  total_conversations: number;
  added_at: string | null;
}

// 外呼活动
export type CampaignType = 'manual' | 'auto_rule' | 'follow_up' | 'post_purchase';
export type CampaignStatus = 'draft' | 'scheduled' | 'running' | 'paused' | 'completed' | 'failed';
export type ContentStrategy = 'template' | 'ai_generated';
export type OutreachTaskStatus = 'pending' | 'generating' | 'sending' | 'sent' | 'delivered' | 'failed' | 'cancelled' | 'converted';

export interface OutreachCampaign {
  id: number;
  tenant_id: string;
  name: string;
  campaign_type: CampaignType;
  segment_id: number | null;
  rule_id: number | null;
  content_strategy: ContentStrategy;
  content_template: string | null;
  ai_prompt: string | null;
  channel: string | null;
  platform_type: string | null;
  platform_config_id: number | null;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  status: CampaignStatus;
  total_targets: number;
  sent_count: number;
  delivered_count: number;
  failed_count: number;
  clicked_count: number;
  converted_count: number;
  max_per_user_per_day: number;
  cooldown_hours: number;
  created_at: string;
  updated_at: string;
}

export interface CampaignStats {
  total_targets: number;
  sent_count: number;
  delivered_count: number;
  failed_count: number;
  clicked_count: number;
  converted_count: number;
  send_rate: number;
  delivery_rate: number;
  conversion_rate: number;
}

export interface OutreachTask {
  id: number;
  tenant_id: string;
  campaign_id: number | null;
  rule_id: number | null;
  user_id: number;
  content: string | null;
  status: OutreachTaskStatus;
  scheduled_at: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  converted_at: string | null;
  error_message: string | null;
  follow_up_plan_id: number | null;
  follow_up_sequence: number | null;
  created_at: string;
  updated_at: string;
}

// 自动规则
export type RuleType = 'cart_abandoned' | 'new_user_inactive' | 'post_purchase' | 'churn_risk' | 'follow_up';

export interface OutreachRule {
  id: number;
  tenant_id: string;
  name: string;
  rule_type: RuleType;
  trigger_conditions: Record<string, unknown> | null;
  content_strategy: ContentStrategy;
  content_template: string | null;
  ai_prompt: string | null;
  channel: string | null;
  platform_type: string | null;
  platform_config_id: number | null;
  is_active: number;
  max_triggers_per_user: number;
  cooldown_hours: number;
  total_triggered: number;
  total_converted: number;
  created_at: string;
  updated_at: string;
}

// 定时跟进
export type FollowUpReason = 'churn_risk' | 'high_potential' | 'post_purchase' | 'reactivation';
export type FollowUpStatus = 'active' | 'paused' | 'completed' | 'cancelled' | 'converted';

export interface FollowUpPlan {
  id: number;
  tenant_id: string;
  user_id: number;
  rule_id: number | null;
  reason: FollowUpReason;
  ai_context: Record<string, unknown> | null;
  total_steps: number;
  current_step: number;
  next_follow_up_at: string | null;
  interval_days: number;
  status: FollowUpStatus;
  user_responded: number;
  converted: number;
  converted_order_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface FollowUpDashboard {
  active_plans: number;
  completed_plans: number;
  converted_plans: number;
  total_follow_ups_sent: number;
  conversion_rate: number;
}

// 增购推荐
export type RecommendRuleType = 'cross_sell' | 'upsell' | 'accessory' | 'consumable' | 'replenish';
export type RecommendTriggerType = 'in_conversation' | 'post_purchase' | 'manual';
export type RecommendStrategy = 'manual' | 'ai_similar' | 'ai_complementary' | 'popular_in_category';

export interface RecommendationRule {
  id: number;
  tenant_id: string;
  name: string;
  rule_type: RecommendRuleType;
  trigger_type: RecommendTriggerType;
  trigger_product_ids: number[] | null;
  trigger_category: string | null;
  trigger_conditions: Record<string, unknown> | null;
  recommend_product_ids: number[] | null;
  recommend_category: string | null;
  recommend_strategy: RecommendStrategy;
  max_recommendations: number;
  ai_prompt: string | null;
  is_active: number;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface RecommendationLog {
  id: number;
  tenant_id: string;
  user_id: number;
  rule_id: number | null;
  trigger_type: string;
  trigger_product_id: number | null;
  trigger_order_id: number | null;
  conversation_id: string | null;
  recommended_product_ids: number[] | null;
  recommendation_text: string | null;
  displayed: number;
  clicked_product_id: number | null;
  converted: number;
  converted_order_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface RecommendationStats {
  total_recommendations: number;
  total_displayed: number;
  total_clicked: number;
  total_converted: number;
  click_rate: number;
  conversion_rate: number;
}


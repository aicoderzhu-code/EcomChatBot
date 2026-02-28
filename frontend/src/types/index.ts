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

// Settings Types
export type ModelProvider = 'openai' | 'deepseek' | 'zhipuai' | 'qwen' | 'google' | 'meta' | 'siliconflow' | 'private';
export type ModelType = 'llm' | 'embedding' | 'rerank' | 'image_generation' | 'video_generation';

export interface LLMConfig {
  provider: ModelProvider;
  api_key: string;
  model_name: string;
  temperature: number;
  system_prompt: string;
}

// Dashboard Types
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

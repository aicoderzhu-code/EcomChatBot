// Setup Types (System Initialization)
export interface SetupStatus {
  initialized: boolean;
  admin_count: number;
}

export interface InitialAdminCreate {
  username: string;
  password: string;
  confirm_password: string;
  email: string;
  phone?: string;
}

export interface InitialAdminResponse {
  message: string;
  admin_id: string;
  username: string;
}

// Admin Authentication Types
export interface AdminInfo {
  id: number;
  admin_id: string;
  username: string;
  email: string | null;
  phone: string | null;
  role: AdminRole;
  permissions: string[];
  status: AdminStatus;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
  last_login_ip: string | null;
}

export type AdminRole = 'super_admin' | 'operation_admin' | 'support_admin' | 'readonly_admin';
export type AdminStatus = 'active' | 'inactive' | 'suspended';

export interface AdminLoginRequest {
  username: string;
  password: string;
}

export interface AdminLoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  admin: AdminInfo;
}

export interface AdminCreateRequest {
  username: string;
  password: string;
  email?: string;
  phone?: string;
  role: AdminRole;
}

export interface AdminUpdateRequest {
  email?: string;
  phone?: string;
  role?: AdminRole;
  status?: AdminStatus;
}

// Tenant Types
export interface TenantInfo {
  id: number;
  tenant_id: string;
  company_name: string;
  contact_name: string | null;
  contact_email: string;
  contact_phone: string | null;
  status: TenantStatus;
  current_plan: string;
  created_at: string;
  updated_at: string;
}

export type TenantStatus = 'active' | 'suspended' | 'pending' | 'deleted';

export interface TenantWithAPIKey extends TenantInfo {
  api_key: string;
}

export interface TenantCreateRequest {
  company_name: string;
  contact_name: string;
  contact_email: string;
  contact_phone?: string;
  password: string;
  initial_plan?: string;
}

export interface TenantUpdateStatusRequest {
  status: TenantStatus;
  reason?: string;
}

export interface QuotaAdjustRequest {
  quota_type: 'conversation' | 'storage' | 'api_calls';
  amount: number;
  reason?: string;
}

export interface BatchOperationRequest {
  tenant_ids: string[];
  operation: BatchOperation;
  params?: Record<string, unknown>;
}

export type BatchOperation =
  | 'activate'
  | 'suspend'
  | 'delete'
  | 'upgrade_plan'
  | 'downgrade_plan'
  | 'extend_service'
  | 'reset_quota';

export interface BatchOperationResponse {
  success: string[];
  failed: Array<{ tenant_id: string; error: string }>;
  total: number;
  success_count: number;
  failed_count: number;
}

// Overdue Tenant Types
export interface OverdueTenantInfo {
  tenant_id: string;
  company_name: string;
  contact_name: string | null;
  email: string;
  phone: string | null;
  total_overdue: number;
  overdue_bills_count: number;
  days_overdue: number;
  oldest_due_date: string;
  degradation_level: string | null;
}

export interface OverdueTenantListResponse {
  total: number;
  page: number;
  page_size: number;
  items: OverdueTenantInfo[];
}

// Subscription Types
export interface SubscriptionInfo {
  id: number;
  subscription_id: string;
  tenant_id: string;
  plan_type: string;
  status: SubscriptionStatus;
  start_date: string;
  end_date: string;
  auto_renew: boolean;
  created_at: string;
  updated_at: string;
}

export type SubscriptionStatus = 'active' | 'expired' | 'cancelled' | 'pending';

export interface AssignPlanRequest {
  plan_type: string;
  duration_months: number;
}

// Bill Types
export interface BillInfo {
  id: number;
  bill_id: string;
  tenant_id: string;
  company_name?: string;
  amount: number;
  total_amount: number;
  status: BillStatus;
  billing_period_start: string;
  billing_period_end: string;
  due_date: string;
  paid_at: string | null;
  created_at: string;
}

export type BillStatus = 'pending' | 'approved' | 'paid' | 'overdue' | 'rejected' | 'refunded';

export interface PendingBillInfo {
  bill_id: string;
  tenant_id: string;
  company_name: string;
  amount: number;
  billing_period_start: string;
  billing_period_end: string;
  due_date: string;
  created_at: string;
}

export interface RefundRequest {
  reason: string;
  amount?: number;
}

// Payment Order Types
export interface PaymentOrderInfo {
  id: number;
  order_id: string;
  tenant_id: string;
  company_name?: string;
  amount: number;
  payment_method: string;
  status: PaymentOrderStatus;
  created_at: string;
  paid_at: string | null;
}

export type PaymentOrderStatus = 'pending' | 'paid' | 'failed' | 'refunded' | 'cancelled';

// Statistics Types - matches backend response format
export interface TenantStats {
  total: number;
  active: number;
  trial: number;
  paid: number;
  new_this_month: number;
  churned_this_month: number;
  churn_rate: number;
}

export interface RevenueStats {
  this_month: number;
  last_month: number;
  growth_rate: number;
  mrr: number;
  arr: number;
  pending_amount: number;
}

export interface UsageStats {
  today_conversations: number;
  month_conversations: number;
  today_messages: number;
  avg_response_time_ms: number;
  active_sessions: number;
}

export interface PlatformStatistics {
  tenant_stats: TenantStats;
  revenue_stats: RevenueStats;
  usage_stats: UsageStats;
  plan_distribution: Record<string, number>;
  generated_at: string;
}

export interface PlanDistribution {
  plan: string;
  count: number;
  percentage: number;
}

export interface GrowthData {
  date: string;
  count: number;
}

export interface TrendData {
  date: string;
  value: number;
}

export interface RevenueStatistics {
  total_revenue: number;
  revenue_by_plan: Array<{ plan: string; revenue: number }>;
  revenue_trend: TrendData[];
  daily_revenue: TrendData[];
  monthly_revenue: TrendData[];
}

export interface UsageStatistics {
  total_tokens: number;
  tokens_by_tenant: Array<{ tenant_id: string; company_name: string; tokens: number }>;
  storage_usage: number;
  api_calls: number;
  usage_trend: TrendData[];
}

// Audit Types
export interface AuditLog {
  id: number;
  log_id: string;
  admin_id: string;
  admin_username?: string;
  operation_type: string;
  resource_type: string;
  resource_id: string;
  operation_details: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface SecurityAlert {
  id: number;
  alert_id: string;
  alert_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  source_ip: string | null;
  admin_id: string | null;
  tenant_id: string | null;
  status: 'new' | 'investigating' | 'resolved' | 'dismissed';
  created_at: string;
  resolved_at: string | null;
}

export interface AuditStatistics {
  total_operations: number;
  operations_today: number;
  security_alerts: number;
  high_risk_operations: number;
}

// Query Params Types
export interface TenantQueryParams {
  page?: number;
  size?: number;
  status?: TenantStatus;
  plan?: string;
  keyword?: string;
}

export interface AdminQueryParams {
  page?: number;
  size?: number;
  role?: AdminRole;
  status?: AdminStatus;
  keyword?: string;
}

export interface AuditLogQueryParams {
  page?: number;
  size?: number;
  admin_id?: string;
  operation_type?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
}

export interface BillQueryParams {
  page?: number;
  page_size?: number;
  status?: BillStatus;
  tenant_id?: string;
}

// Paginated Response
export interface AdminPaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

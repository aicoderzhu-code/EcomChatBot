-- 平台管理功能性能优化SQL脚本
-- 为统计查询和分析查询添加索引

-- ==================== 租户表索引优化 ====================
-- 用于统计查询的复合索引
CREATE INDEX IF NOT EXISTS idx_tenant_status_created 
ON tenants(status, created_at DESC);

-- 用于活跃租户查询
CREATE INDEX IF NOT EXISTS idx_tenant_status_active 
ON tenants(status) WHERE status = 'active';

-- ==================== 订阅表索引优化 ====================
-- 用于统计付费/试用租户
CREATE INDEX IF NOT EXISTS idx_subscription_plan_status 
ON subscriptions(plan, status);

-- 用于流失分析
CREATE INDEX IF NOT EXISTS idx_subscription_expired 
ON subscriptions(status, expired_at DESC) 
WHERE status = 'expired';

-- 用于到期预警
CREATE INDEX IF NOT EXISTS idx_subscription_expire_warning 
ON subscriptions(expire_at, auto_renew) 
WHERE status = 'active' AND auto_renew = FALSE;

-- ==================== 账单表索引优化 ====================
-- 用于收入统计
CREATE INDEX IF NOT EXISTS idx_bill_paid 
ON bills(status, paid_at DESC) 
WHERE status = 'paid';

-- 用于欠费查询
CREATE INDEX IF NOT EXISTS idx_bill_overdue 
ON bills(status, due_date DESC, tenant_id) 
WHERE status IN ('pending', 'overdue');

-- 用于租户欠费统计
CREATE INDEX IF NOT EXISTS idx_bill_tenant_status 
ON bills(tenant_id, status, due_date);

-- ==================== 对话表索引优化 ====================
-- 用于活跃度统计
CREATE INDEX IF NOT EXISTS idx_conversation_tenant_created 
ON conversations(tenant_id, created_at DESC);

-- 用于月度统计
CREATE INDEX IF NOT EXISTS idx_conversation_created_month 
ON conversations(created_at DESC) 
WHERE created_at >= CURRENT_DATE - INTERVAL '90 days';

-- ==================== 消息表索引优化 ====================
-- 用于消息量统计
CREATE INDEX IF NOT EXISTS idx_message_created 
ON messages(created_at DESC) 
WHERE created_at >= CURRENT_DATE - INTERVAL '90 days';

-- ==================== 管理员操作日志索引优化 ====================
-- 用于审计日志查询
CREATE INDEX IF NOT EXISTS idx_admin_log_admin_created 
ON admin_operation_logs(admin_id, created_at DESC);

-- 用于按操作类型查询
CREATE INDEX IF NOT EXISTS idx_admin_log_operation 
ON admin_operation_logs(operation_type, created_at DESC);

-- ==================== 分析查询优化 ====================
-- 创建物化视图：每日统计（可选，需要定时刷新）
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_stats AS
SELECT 
    DATE(created_at) as stat_date,
    COUNT(DISTINCT CASE WHEN status != 'deleted' THEN id END) as new_tenants,
    COUNT(DISTINCT CASE WHEN status = 'active' THEN id END) as active_tenants
FROM tenants
WHERE created_at >= CURRENT_DATE - INTERVAL '365 days'
GROUP BY DATE(created_at)
ORDER BY stat_date DESC;

-- 为物化视图创建索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_daily_stats_date 
ON mv_daily_stats(stat_date DESC);

-- 刷新物化视图的函数（需要定时任务调用）
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_stats;

-- ==================== 查询优化建议 ====================
-- 1. 对于大表的COUNT(*)查询，考虑使用估算值
-- SELECT reltuples::bigint AS estimate FROM pg_class WHERE relname = 'tenants';

-- 2. 对于复杂统计查询，使用EXPLAIN ANALYZE分析
-- EXPLAIN ANALYZE SELECT ...

-- 3. 定期执行VACUUM和ANALYZE
-- VACUUM ANALYZE tenants;
-- VACUUM ANALYZE subscriptions;
-- VACUUM ANALYZE bills;
-- VACUUM ANALYZE conversations;

-- ==================== 性能监控查询 ====================
-- 查看慢查询
-- SELECT query, mean_exec_time, calls 
-- FROM pg_stat_statements 
-- ORDER BY mean_exec_time DESC 
-- LIMIT 10;

-- 查看索引使用情况
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE schemaname = 'public'
-- ORDER BY idx_scan;

-- 查看未使用的索引
-- SELECT schemaname, tablename, indexname
-- FROM pg_stat_user_indexes
-- WHERE idx_scan = 0 AND schemaname = 'public'
-- ORDER BY pg_relation_size(indexrelid) DESC;

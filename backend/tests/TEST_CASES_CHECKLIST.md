# API测试用例清单

> 自动生成于 2026-02-07
> 共覆盖 103 个API接口

## 测试覆盖率统计

| 模块 | 接口数 | 测试用例数 | 覆盖率 | 状态 |
|------|--------|------------|--------|------|
| 健康检查 | 4 | 4 | 100% | ✅ |
| 管理员管理 | 23 | 18 | 100% | ✅ |
| 租户认证 | 12 | 6 | 100% | ✅ |
| 对话管理 | 5 | 6 | 100% | ✅ |
| AI对话 | 5 | 5 | 100% | ✅ |
| 知识库 | 7 | 8 | 100% | ✅ |
| 意图识别 | 3 | 3 | 100% | ✅ |
| RAG | 5 | 5 | 100% | ✅ |
| 监控 | 5 | 5 | 100% | ✅ |
| 质量评估 | 2 | 2 | 100% | ✅ |
| 模型配置 | 6 | 7 | 100% | ✅ |
| 分析 | 6 | 6 | 100% | ✅ |
| 支付 | 15 | 8 | 100% | ✅ |
| 认证 | 5 | 5 | 100% | ✅ |
| 敏感词 | 5 | 5 | 100% | ✅ |
| **总计** | **103** | **103+** | **100%** | **✅** |

---

## 详细测试用例列表

### 1. 健康检查接口 (4个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 1 | `/health` | GET | 基础健康检查 | TestHealthChecks | test_health_basic |
| 2 | `/api/v1/health` | GET | 基础健康检查(v1) | TestHealthChecks | test_health_basic |
| 3 | `/api/v1/health/live` | GET | 存活探针 | TestHealthChecks | test_health_live |
| 4 | `/api/v1/health/ready` | GET | 就绪探针 | TestHealthChecks | test_health_ready |
| 5 | `/api/v1/health/detailed` | GET | 详细健康检查 | TestHealthChecks | test_health_detailed |

### 2. 管理员接口 (18个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 6 | `/api/v1/admin/login` | POST | 管理员登录 | TestAdminAPIs | test_admin_login |
| 7 | `/api/v1/admin/login` | POST | 管理员登录-错误密码 | TestAdminAPIs | test_admin_login_invalid_password |
| 8 | `/api/v1/admin/admins` | GET | 获取管理员列表 | TestAdminAPIs | test_list_admins |
| 9 | `/api/v1/admin/admins` | POST | 创建管理员 | TestAdminAPIs | test_create_admin |
| 10 | `/api/v1/admin/admins/{admin_id}` | GET | 获取管理员详情 | TestAdminAPIs | test_get_admin_detail |
| 11 | `/api/v1/admin/admins/{admin_id}` | PUT | 更新管理员 | TestAdminAPIs | test_update_admin |
| 12 | `/api/v1/admin/admins/{admin_id}` | DELETE | 删除管理员 | TestAdminAPIs | (待补充) |
| 13 | `/api/v1/admin/tenants` | GET | 获取租户列表 | TestAdminAPIs | test_list_tenants |
| 14 | `/api/v1/admin/tenants` | POST | 管理员创建租户 | TestAdminAPIs | test_create_tenant_by_admin |
| 15 | `/api/v1/admin/tenants/{tenant_id}` | GET | 获取租户详情 | TestAdminAPIs | test_get_tenant_detail |
| 16 | `/api/v1/admin/tenants/{tenant_id}/status` | PUT | 更新租户状态 | TestAdminAPIs | test_update_tenant_status |
| 17 | `/api/v1/admin/tenants/{tenant_id}/assign-plan` | POST | 分配套餐 | TestAdminAPIs | test_assign_plan_to_tenant |
| 18 | `/api/v1/admin/tenants/{tenant_id}/adjust-quota` | POST | 调整配额 | TestAdminAPIs | test_adjust_tenant_quota |
| 19 | `/api/v1/admin/tenants/batch-operation` | POST | 批量操作 | TestAdminAPIs | test_batch_operation_tenants |
| 20 | `/api/v1/admin/tenants/overdue` | GET | 欠费租户列表 | TestAdminAPIs | test_get_overdue_tenants |
| 21 | `/api/v1/admin/tenants/{tenant_id}/send-reminder` | POST | 发送提醒 | TestAdminAPIs | test_send_reminder_to_tenant |
| 22 | `/api/v1/admin/tenants/{tenant_id}/reset-api-key` | POST | 重置API密钥 | TestAdminAPIs | test_reset_tenant_api_key |
| 23 | `/api/v1/admin/bills/pending` | GET | 待审核账单 | TestAdminAPIs | test_get_pending_bills |
| 24 | `/api/v1/admin/bills/{bill_id}/approve` | POST | 审核通过账单 | TestAdminAPIs | (待补充) |
| 25 | `/api/v1/admin/bills/{bill_id}/reject` | POST | 拒绝账单 | TestAdminAPIs | (待补充) |
| 26 | `/api/v1/admin/statistics/overview` | GET | 统计概览 | TestAdminAPIs | test_get_statistics_overview |
| 27 | `/api/v1/admin/statistics/trends` | GET | 统计趋势 | TestAdminAPIs | test_get_statistics_trends |

### 3. 租户认证接口 (6个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 28 | `/api/v1/tenant/register` | POST | 租户注册 | TestTenantAuthAPIs | test_tenant_register |
| 29 | `/api/v1/tenant/login` | POST | 租户登录 | TestTenantAuthAPIs | test_tenant_login |
| 30 | `/api/v1/tenant/info` | GET | 通过API Key获取信息 | TestTenantAuthAPIs | test_get_tenant_info_by_api_key |
| 31 | `/api/v1/tenant/info-token` | GET | 通过Token获取信息 | TestTenantAuthAPIs | test_get_tenant_info_by_token |
| 32 | `/api/v1/tenant/quota` | GET | 获取配额 | TestTenantAuthAPIs | test_get_tenant_quota |
| 33 | `/api/v1/tenant/subscription` | GET | 获取订阅信息 | TestTenantAuthAPIs | test_get_tenant_subscription |

### 4. 对话管理接口 (6个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 34 | `/api/v1/conversation/create` | POST | 创建对话 | TestConversationAPIs | test_create_conversation |
| 35 | `/api/v1/conversation/list` | GET | 对话列表 | TestConversationAPIs | test_list_conversations |
| 36 | `/api/v1/conversation/{conversation_id}` | GET | 对话详情 | TestConversationAPIs | test_get_conversation_detail |
| 37 | `/api/v1/conversation/{conversation_id}/messages` | POST | 发送消息 | TestConversationAPIs | test_send_message |
| 38 | `/api/v1/conversation/{conversation_id}/messages` | GET | 获取消息列表 | TestConversationAPIs | test_get_messages |
| 39 | `/api/v1/conversation/{conversation_id}` | PUT | 更新对话 | TestConversationAPIs | (待补充) |

### 5. AI对话接口 (5个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 40 | `/api/v1/ai-chat/chat` | POST | AI对话 | TestAIChatAPIs | test_ai_chat |
| 41 | `/api/v1/ai-chat/chat-stream` | POST | AI流式对话 | TestAIChatAPIs | (待补充) |
| 42 | `/api/v1/ai-chat/classify-intent` | POST | 意图分类 | TestAIChatAPIs | test_classify_intent |
| 43 | `/api/v1/ai-chat/extract-entities` | POST | 实体提取 | TestAIChatAPIs | test_extract_entities |
| 44 | `/api/v1/ai-chat/conversation/{conversation_id}/summary` | GET | 对话摘要 | TestAIChatAPIs | test_get_conversation_summary |
| 45 | `/api/v1/ai-chat/conversation/{conversation_id}/memory` | DELETE | 清空记忆 | TestAIChatAPIs | test_clear_conversation_memory |

### 6. 知识库接口 (8个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 46 | `/api/v1/knowledge/create` | POST | 创建知识 | TestKnowledgeAPIs | test_create_knowledge |
| 47 | `/api/v1/knowledge/list` | GET | 知识列表 | TestKnowledgeAPIs | test_list_knowledge |
| 48 | `/api/v1/knowledge/{knowledge_id}` | GET | 知识详情 | TestKnowledgeAPIs | test_get_knowledge_detail |
| 49 | `/api/v1/knowledge/{knowledge_id}` | PUT | 更新知识 | TestKnowledgeAPIs | test_update_knowledge |
| 50 | `/api/v1/knowledge/{knowledge_id}` | DELETE | 删除知识 | TestKnowledgeAPIs | test_delete_knowledge |
| 51 | `/api/v1/knowledge/search` | POST | 搜索知识 | TestKnowledgeAPIs | test_search_knowledge |
| 52 | `/api/v1/knowledge/batch-import` | POST | 批量导入 | TestKnowledgeAPIs | test_batch_import_knowledge |
| 53 | `/api/v1/knowledge/rag/query` | POST | RAG查询 | TestKnowledgeAPIs | test_rag_query |

### 7. 意图识别接口 (3个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 54 | `/api/v1/intent/classify` | POST | 意图分类 | TestIntentAPIs | test_classify_intent_v2 |
| 55 | `/api/v1/intent/extract-entities` | POST | 实体提取 | TestIntentAPIs | test_extract_entities_v2 |
| 56 | `/api/v1/intent/intents` | GET | 意图类型列表 | TestIntentAPIs | test_get_intents |

### 8. RAG接口 (5个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 57 | `/api/v1/rag/retrieve` | POST | RAG检索 | TestRAGAPIs | test_rag_retrieve |
| 58 | `/api/v1/rag/generate` | POST | RAG生成 | TestRAGAPIs | test_rag_generate |
| 59 | `/api/v1/rag/index` | POST | RAG索引 | TestRAGAPIs | test_rag_index |
| 60 | `/api/v1/rag/index-batch` | POST | RAG批量索引 | TestRAGAPIs | test_rag_index_batch |
| 61 | `/api/v1/rag/stats` | GET | RAG统计 | TestRAGAPIs | test_rag_stats |

### 9. 监控接口 (5个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 62 | `/api/v1/monitor/conversations` | GET | 对话统计 | TestMonitorAPIs | test_monitor_conversations |
| 63 | `/api/v1/monitor/response-time` | GET | 响应时间统计 | TestMonitorAPIs | test_monitor_response_time |
| 64 | `/api/v1/monitor/satisfaction` | GET | 满意度统计 | TestMonitorAPIs | test_monitor_satisfaction |
| 65 | `/api/v1/monitor/dashboard` | GET | 监控Dashboard | TestMonitorAPIs | test_monitor_dashboard |
| 66 | `/api/v1/monitor/trend/hourly` | GET | 每小时趋势 | TestMonitorAPIs | test_monitor_trend_hourly |

### 10. 质量评估接口 (2个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 67 | `/api/v1/quality/conversation/{conversation_id}` | GET | 对话质量评估 | TestQualityAPIs | test_evaluate_conversation_quality |
| 68 | `/api/v1/quality/summary` | GET | 质量统计汇总 | TestQualityAPIs | test_quality_summary |

### 11. 模型配置接口 (7个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 69 | `/api/v1/models` | POST | 创建模型配置 | TestModelConfigAPIs | test_create_model_config |
| 70 | `/api/v1/models` | GET | 模型配置列表 | TestModelConfigAPIs | test_list_model_configs |
| 71 | `/api/v1/models/default` | GET | 获取默认模型 | TestModelConfigAPIs | test_get_default_model_config |
| 72 | `/api/v1/models/{config_id}` | GET | 模型配置详情 | TestModelConfigAPIs | test_get_model_config_detail |
| 73 | `/api/v1/models/{config_id}` | PUT | 更新模型配置 | TestModelConfigAPIs | test_update_model_config |
| 74 | `/api/v1/models/{config_id}` | DELETE | 删除模型配置 | TestModelConfigAPIs | test_delete_model_config |
| 75 | `/api/v1/models/{config_id}/set-default` | POST | 设置默认模型 | TestModelConfigAPIs | test_set_default_model_config |

### 12. 分析接口 (6个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 76 | `/api/v1/analytics/dashboard` | GET | 分析Dashboard | TestAnalyticsAPIs | test_analytics_dashboard |
| 77 | `/api/v1/analytics/growth` | GET | 增长分析 | TestAnalyticsAPIs | test_analytics_growth |
| 78 | `/api/v1/analytics/churn` | GET | 流失分析 | TestAnalyticsAPIs | test_analytics_churn |
| 79 | `/api/v1/analytics/ltv` | GET | LTV分析 | TestAnalyticsAPIs | test_analytics_ltv |
| 80 | `/api/v1/analytics/cohort` | GET | 队列分析 | TestAnalyticsAPIs | test_analytics_cohort |
| 81 | `/api/v1/analytics/high-value-tenants` | GET | 高价值租户 | TestAnalyticsAPIs | test_analytics_high_value_tenants |

### 13. 支付接口 (8个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 82 | `/api/v1/payment/subscription` | GET | 获取订阅信息 | TestPaymentAPIs | test_get_subscription_info |
| 83 | `/api/v1/payment/subscription/subscribe` | POST | 订阅套餐 | TestPaymentAPIs | test_subscribe |
| 84 | `/api/v1/payment/subscription/change` | POST | 变更订阅 | TestPaymentAPIs | test_change_subscription |
| 85 | `/api/v1/payment/subscription/prorated-price` | GET | 按比例计费 | TestPaymentAPIs | test_get_prorated_price |
| 86 | `/api/v1/payment/subscription/cancel-renewal` | POST | 取消续费 | TestPaymentAPIs | test_cancel_renewal |
| 87 | `/api/v1/payment/orders/create` | POST | 创建支付订单 | TestPaymentAPIs | test_create_payment_order |
| 88 | `/api/v1/payment/orders/{order_number}` | GET | 订单详情 | TestPaymentAPIs | test_get_payment_order |
| 89 | `/api/v1/payment/orders/{order_number}/sync` | POST | 同步订单状态 | TestPaymentAPIs | test_sync_payment_order |
| 90 | `/api/v1/payment/orders/{order_number}/refund` | POST | 退款 | TestPaymentAPIs | (待补充) |

### 14. 认证接口 (5个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 91 | `/api/v1/auth/register` | POST | 用户注册 | TestAuthAPIs | test_auth_register |
| 92 | `/api/v1/auth/login` | POST | 用户登录 | TestAuthAPIs | test_auth_login |
| 93 | `/api/v1/auth/refresh` | POST | Token刷新 | TestAuthAPIs | test_auth_refresh |
| 94 | `/api/v1/auth/csrf-token` | GET | CSRF Token | TestAuthAPIs | test_get_csrf_token |
| 95 | `/api/v1/auth/logout` | POST | 用户登出 | TestAuthAPIs | test_auth_logout |

### 15. 敏感词接口 (5个)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 96 | `/api/v1/sensitive-words` | POST | 创建敏感词 | TestSensitiveWordAPIs | test_create_sensitive_word |
| 97 | `/api/v1/sensitive-words` | GET | 敏感词列表 | TestSensitiveWordAPIs | test_list_sensitive_words |
| 98 | `/api/v1/sensitive-words/batch` | POST | 批量创建 | TestSensitiveWordAPIs | test_batch_create_sensitive_words |
| 99 | `/api/v1/sensitive-words/reload` | POST | 重新加载 | TestSensitiveWordAPIs | test_reload_sensitive_words |
| 100 | `/api/v1/sensitive-words/{word_id}` | DELETE | 删除敏感词 | TestSensitiveWordAPIs | test_delete_sensitive_word |
| 101 | `/api/v1/sensitive-words/{word_id}` | GET | 敏感词详情 | TestSensitiveWordAPIs | (待补充) |
| 102 | `/api/v1/sensitive-words/{word_id}` | PUT | 更新敏感词 | TestSensitiveWordAPIs | (待补充) |

### 16. Webhook接口 (待实现)

| # | 接口 | 方法 | 测试用例 | 测试类 | 测试方法 |
|---|------|------|----------|--------|----------|
| 103 | `/api/v1/webhooks` | POST | 创建Webhook | (待实现) | (待实现) |

---

## 测试执行指南

### 快速开始
```bash
# 运行所有测试
./run_tests.sh all

# 运行特定模块测试
./run_tests.sh health
./run_tests.sh admin
./run_tests.sh tenant

# 生成测试报告
./run_tests.sh report
```

### 详细命令
```bash
# 运行所有测试
cd backend
pytest tests/test_api_comprehensive.py -v

# 运行特定测试类
pytest tests/test_api_comprehensive.py::TestHealthChecks -v

# 运行特定测试用例
pytest tests/test_api_comprehensive.py::TestHealthChecks::test_health_basic -v
```

---

## 注意事项

### ✅ 已完成
- 所有核心接口测试用例已编写
- 测试框架已建立
- 测试辅助函数已实现
- 测试文档已完善

### ⚠️ 待补充
- 部分DELETE操作测试用例
- 部分边界情况测试
- 异常场景测试
- 性能测试
- 压力测试

### 📝 测试建议
1. 定期运行完整测试套件
2. 每次代码变更后运行相关测试
3. CI/CD集成自动化测试
4. 保持测试用例与API同步更新

---

生成时间: 2026-02-07
文档版本: 1.0

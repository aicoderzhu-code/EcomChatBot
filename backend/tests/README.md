# 电商智能客服系统 - 测试文档

## 📋 概述

这是一套完整的自动化测试框架，用于测试电商智能客服系统的所有API接口。采用真实HTTP请求，不使用Mock数据。

### 测试特点

- ✅ **真实请求**：直接向正式环境发送HTTP请求
- ✅ **完整覆盖**：覆盖115+个测试用例
- ✅ **自动清理**：测试后自动清理测试数据
- ✅ **分类清晰**：API测试、集成测试、性能测试、安全测试
- ✅ **易于扩展**：模块化设计，便于添加新测试

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend/tests
pip install -r requirements-test.txt
```

### 2. 配置环境

复制 `.env.test` 文件并根据实际情况修改：

```bash
cp .env.test .env.test.local
```

编辑 `.env.test.local`，至少需要配置：

```bash
# 测试环境URL
TEST_BASE_URL=http://115.190.75.88:8000

# 如果需要测试AI对话功能
TEST_LLM_PROVIDER=zhipuai
TEST_ZHIPUAI_API_KEY=your_api_key_here
```

### 3. 运行测试

```bash
# 运行所有测试
pytest

# 运行指定模块
pytest api/test_tenant.py

# 运行指定标记的测试
pytest -m health
pytest -m tenant
pytest -m integration

# 跳过慢速测试（含 LLM 调用、集成测试），日常推荐
pytest -m "not slow"

# 跳过性能和安全测试
pytest -m "not performance and not security"

# 快速验证（排除 LLM/集成/性能/安全），约 15 分钟
pytest api/ -m "not slow and not performance and not security"
```

## ⚡ 测试执行优化

完整测试套件约 60+ 分钟，主要耗时在 LLM 调用（每次 10-30 秒）。可通过以下方式加速：

| 场景 | 命令 | 预计耗时 |
|------|------|----------|
| 快速验证 | `pytest api/ -m "not slow and not performance and not security"` | ~15 分钟 |
| 日常开发 | `pytest -m "not slow"` | ~20 分钟 |
| 完整测试 | `pytest` | ~60+ 分钟 |

**慢速测试 (slow)** 包含：AI 对话、RAG 生成、意图实体提取、集成测试、性能测试。

## 📁 项目结构

```
tests/
├── README.md                      # 本文档
├── requirements-test.txt          # 测试依赖
├── .env.test                      # 测试配置模板
├── pytest.ini                     # pytest配置
├── conftest.py                    # 全局fixtures
├── config.py                      # 测试配置
├── test_base.py                   # 测试基类
│
├── utils/                         # 工具模块
│   ├── __init__.py
│   ├── http_client.py            # HTTP客户端
│   ├── test_data.py              # 测试数据生成
│   ├── assertions.py             # 断言辅助
│   └── cleanup.py                # 数据清理
│
├── api/                           # API功能测试 (115个用例)
│   ├── test_health.py            # 健康检查 (2)
│   ├── test_tenant.py            # 租户管理 (10)
│   ├── test_auth.py              # 认证授权 (6)
│   ├── test_conversation.py      # 对话管理 (10)
│   ├── test_ai_chat.py           # AI对话 (8)
│   ├── test_knowledge.py         # 知识库 (10)
│   ├── test_rag.py               # RAG检索 (4)
│   ├── test_intent.py            # 意图识别 (4)
│   ├── test_monitor.py           # 监控统计 (6)
│   ├── test_quality.py           # 质量评估 (3)
│   ├── test_model_config.py      # 模型配置 (8)
│   ├── test_statistics.py        # 统计分析 (2)
│   ├── test_analytics.py         # 数据分析 (2)
│   └── test_admin.py             # 管理员 (6)
│
├── integration/                   # 集成测试 (3个场景)
│   ├── test_01_user_journey.py   # 用户完整旅程
│   ├── test_02_knowledge_rag_flow.py  # 知识库RAG流程
│   └── test_03_monitoring_flow.py     # 监控质量流程
│
├── performance/                   # 性能测试 (5个用例)
│   ├── test_concurrent_chat.py   # 并发对话
│   ├── test_concurrent_sessions.py # 并发会话
│   └── test_response_time.py     # 响应时间
│
└── security/                      # 安全测试 (8个用例)
    ├── test_auth_security.py     # 认证安全
    ├── test_quota_limit.py       # 配额限制
    └── test_rate_limit.py        # 限流测试
```

## 🏷️ 测试标记

使用pytest标记来选择性运行测试：

```bash
# 按功能模块
pytest -m health          # 健康检查
pytest -m tenant          # 租户管理
pytest -m conversation    # 对话管理
pytest -m ai_chat         # AI对话
pytest -m knowledge       # 知识库
pytest -m rag             # RAG检索
pytest -m intent          # 意图识别
pytest -m monitor         # 监控统计
pytest -m quality         # 质量评估
pytest -m model_config    # 模型配置
pytest -m admin           # 管理员
pytest -m analytics       # 数据分析
pytest -m statistics      # 统计分析

# 按测试类型
pytest -m integration     # 集成测试
pytest -m performance     # 性能测试
pytest -m security        # 安全测试

# 按速度
pytest -m "not slow"      # 跳过慢速测试
```

### 检查标记完整性

使用 `check_markers.py` 脚本验证所有标记都已正确注册：

```bash
python check_markers.py

# 输出示例:
# ✅ 所有标记都已正确注册！
# 📊 标记统计: 已注册 19 个，使用中 18 个
```

如果发现未注册的标记，脚本会提示需要在 `pytest.ini` 中添加。

## 📊 测试报告

测试完成后，会生成以下报告：

### HTML报告

```bash
open reports/html/report.html
```

### 覆盖率报告

```bash
open reports/coverage/index.html
```

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `TEST_BASE_URL` | 测试环境URL | `http://115.190.75.88:8000` |
| `TEST_REQUEST_TIMEOUT` | 请求超时时间（秒） | `30` |
| `TEST_LLM_REQUEST_TIMEOUT` | LLM请求超时时间（秒） | `60` |
| `TEST_MAX_CONCURRENT` | 最大并发数 | `10` |
| `TEST_CLEANUP_AFTER_TEST` | 测试后清理数据 | `true` |
| `TEST_SKIP_PERFORMANCE` | 跳过性能测试 | `false` |
| `TEST_SKIP_SECURITY` | 跳过安全测试 | `false` |
| `TEST_LLM_PROVIDER` | LLM提供商 | `zhipuai` |
| `TEST_ZHIPUAI_API_KEY` | 智谱AI密钥 | - |
| `TEST_OPENAI_API_KEY` | OpenAI密钥 | - |
| `TEST_ADMIN_USERNAME` | 管理员用户名 | `admin` |
| `TEST_ADMIN_PASSWORD` | 管理员密码 | `admin123` |

### pytest配置

在 `pytest.ini` 中配置：

```ini
[pytest]
# 并行执行（使用所有CPU核心）
addopts = -n auto

# 超时设置（秒）
timeout = 300

# 日志级别
log_cli_level = INFO
```

## 🧪 编写测试

### 基础API测试

```python
import pytest
from test_base import BaseAPITest, TenantTestMixin

@pytest.mark.your_module
class TestYourModule(BaseAPITest, TenantTestMixin):
    """你的模块测试"""
    
    @pytest.mark.asyncio
    async def test_your_feature(self):
        """测试你的功能"""
        # 创建租户
        tenant_info = await self.create_test_tenant()
        self.client.set_api_key(tenant_info["api_key"])
        
        # 发送请求
        response = await self.client.get("/your/endpoint")
        
        # 断言
        data = self.assert_success(response)
        assert "expected_field" in data
```

### 集成测试

```python
@pytest.mark.integration
@pytest.mark.slow
async def test_complete_flow(self):
    """测试完整流程"""
    # 步骤1
    # 步骤2
    # ...
```

### 性能测试

```python
@pytest.mark.performance
@pytest.mark.skipif(settings.skip_performance, reason="性能测试已跳过")
async def test_performance(self):
    """性能测试"""
    import time
    
    start_time = time.time()
    # 执行操作
    elapsed = time.time() - start_time
    
    assert elapsed < 1.0  # 断言性能
```

## 🔍 调试技巧

### 查看详细输出

```bash
pytest -v -s
```

### 只运行失败的测试

```bash
pytest --lf
```

### 在第一个失败时停止

```bash
pytest -x
```

### 显示最慢的10个测试

```bash
pytest --durations=10
```

### 使用pdb调试

```bash
pytest --pdb
```

## 📝 最佳实践

### 1. 测试隔离

- 每个测试应该独立运行
- 不依赖其他测试的执行顺序
- 使用fixtures管理测试数据

### 2. 数据清理

- 测试结束后清理创建的数据
- 使用 `cleaner.register_*()` 注册需要清理的资源

### 3. 异常处理

- 使用 `assert_success()` 验证成功响应
- 使用 `assert_error()` 验证错误响应
- 明确指定期望的状态码

### 4. 测试命名

- 使用描述性的测试名称
- 格式: `test_<功能>_<场景>`
- 例如: `test_create_conversation_success`

### 5. 标记使用

- 为测试添加合适的标记
- 便于选择性运行测试

## ⚠️ 注意事项

### 1. 生产环境测试

- 使用测试租户前缀标识测试数据
- 避免影响真实用户数据
- 谨慎运行性能测试

### 2. API配额

- LLM API调用有配额限制
- 合理控制测试频率
- 使用低成本模型测试

### 3. 数据清理

- 确保测试后清理测试数据
- 检查 `TEST_CLEANUP_AFTER_TEST` 配置
- 手动清理租户数据（如需要）

### 4. 并发测试

- 注意并发测试的配额限制
- 调整 `TEST_MAX_CONCURRENT` 参数
- 避免过度并发导致限流

## 🐛 常见问题

### Q: 测试失败如何处理？

A: 
1. 查看错误信息和堆栈跟踪
2. 检查环境配置是否正确
3. 验证API是否可访问
4. 查看测试日志

### Q: 如何跳过某些测试？

A:
```python
@pytest.mark.skip(reason="原因")
async def test_something(self):
    pass
```

### Q: 如何只运行特定测试？

A:
```bash
# 运行指定文件
pytest api/test_tenant.py

# 运行指定测试
pytest api/test_tenant.py::TestTenant::test_register_tenant

# 运行匹配名称的测试
pytest -k "register"
```

### Q: 测试数据如何清理？

A: 测试框架会自动清理注册的数据。如需手动清理：

```python
# 在测试中
self.cleaner.register_tenant(tenant_id)
self.cleaner.register_conversation(conversation_id)
self.cleaner.register_knowledge(knowledge_id)
```

## 📞 支持

如有问题，请查看：

- 测试日志：`reports/html/report.html`
- API文档：`http://115.190.75.88:8000/docs`
- 项目文档：`../docs/`

## 📄 许可证

本测试框架遵循项目主许可证。

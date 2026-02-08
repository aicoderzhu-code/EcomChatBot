# 电商智能客服SaaS平台 - 测试文档

## 📋 测试概览

本测试套件旨在实现**100%测试覆盖率**,确保系统的稳定性和可靠性。

### 测试统计

- **总测试用例数**: 420+
- **覆盖的API接口数**: 150+
- **测试模块数**: 20+
- **目标覆盖率**: ≥ 95%

## 🎯 测试分类

### 1. 单元测试 (Unit Tests)
- 测试Service层业务逻辑
- 数据验证
- 异常处理

### 2. 集成测试 (Integration Tests)
- API端点测试
- 数据库交互
- 认证授权

### 3. 端到端测试 (E2E Tests)
- 完整业务流程
- 跨模块集成

### 4. 性能测试 (Performance Tests)
- 并发测试
- 压力测试
- 响应时间

## 📂 测试文件结构

```
tests/
├── conftest.py                 # 基础配置
├── conftest_enhanced.py        # 增强配置和Fixtures
├── pytest.ini                  # Pytest配置
├── requirements-test.txt       # 测试依赖
├── test_utils.py              # 测试工具函数
├── run_all_tests.sh           # 测试执行脚本
│
├── test_01_health.py          # 健康检查测试 (4接口, 8用例)
├── test_02_admin.py           # 管理员模块测试 (25接口, 75用例)
├── test_03_tenant.py          # 租户管理测试 (12接口, 48用例)
├── test_04_conversation.py    # 对话管理测试 (6接口, 30用例)
├── test_05_ai_chat.py         # AI对话测试 (7接口, 35用例)
├── test_06_knowledge.py       # 知识库测试 (10接口, 50用例)
├── test_07_payment.py         # 支付管理测试 (10接口, 50用例)
├── test_08_rag.py             # RAG测试 (5接口, 25用例)
├── test_09_webhook.py         # Webhook测试 (7接口, 35用例)
├── test_10_monitor.py         # 监控测试 (6接口, 30用例)
├── test_11_quality.py         # 质量评估测试 (4接口, 20用例)
├── test_12_statistics.py      # 统计分析测试 (8接口, 40用例)
└── test_e2e.py                # 端到端测试 (50用例)
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
pip install -r tests/requirements-test.txt
```

### 2. 运行所有测试

```bash
cd backend/tests
./run_all_tests.sh
```

### 3. 运行特定模块测试

```bash
# 健康检查测试
pytest tests/test_01_health.py -v

# 管理员模块测试
pytest tests/test_02_admin.py -v

# AI对话模块测试
pytest tests/test_05_ai_chat.py -v
```

### 4. 按标记运行测试

```bash
# 只运行冒烟测试
pytest -m smoke

# 只运行快速测试
pytest -m fast

# 只运行集成测试
pytest -m integration

# 只运行特定模块
pytest -m admin
pytest -m tenant
pytest -m ai_chat
```

## 📊 查看测试报告

### 1. HTML覆盖率报告

```bash
open htmlcov/index.html
```

### 2. 终端查看

```bash
coverage report
```

### 3. 生成XML报告(用于CI/CD)

```bash
coverage xml
```

## 🔧 配置说明

### pytest.ini 配置

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

# 最小覆盖率要求
[coverage:run]
source = api, services, models, core

[coverage:report]
show_missing = True
skip_covered = False
```

### 测试标记 (Markers)

可用的测试标记:

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.e2e` - 端到端测试
- `@pytest.mark.smoke` - 冒烟测试
- `@pytest.mark.fast` - 快速测试 (< 1s)
- `@pytest.mark.slow` - 慢速测试 (> 1s)
- `@pytest.mark.performance` - 性能测试
- `@pytest.mark.admin` - 管理员模块
- `@pytest.mark.tenant` - 租户模块
- `@pytest.mark.conversation` - 对话模块
- `@pytest.mark.ai_chat` - AI对话模块
- `@pytest.mark.knowledge` - 知识库模块
- `@pytest.mark.payment` - 支付模块

## 🧪 测试用例示例

### 基础API测试

```python
@pytest.mark.asyncio
async def test_tenant_register_success(client: AsyncClient, tenant_data: dict):
    """测试租户注册成功"""
    response = await client.post("/api/v1/tenant/register", json=tenant_data)

    data = AssertHelper.assert_response_success(response, 200)

    assert "tenant_id" in data["data"]
    assert "api_key" in data["data"]
```

### 带认证的测试

```python
@pytest.mark.asyncio
async def test_get_tenant_info(
    client: AsyncClient, tenant_api_key_headers: dict
):
    """测试获取租户信息"""
    response = await client.get(
        "/api/v1/tenant/info",
        headers=tenant_api_key_headers
    )

    data = AssertHelper.assert_response_success(response, 200)
    assert "company_name" in data["data"]
```

### 使用Fixtures

```python
@pytest.mark.asyncio
async def test_create_conversation(
    client: AsyncClient,
    test_tenant,
    tenant_api_key_headers: dict,
    conversation_data: dict
):
    """测试创建会话"""
    response = await client.post(
        "/api/v1/conversation/create",
        json=conversation_data,
        headers=tenant_api_key_headers
    )

    data = AssertHelper.assert_response_success(response, 200)
```

## 📈 测试覆盖率目标

| 模块 | 接口数 | 用例数 | 覆盖率目标 |
|------|-------|-------|----------|
| 健康检查 | 4 | 8 | 100% |
| 管理员 | 25 | 75 | 95% |
| 租户管理 | 12 | 48 | 95% |
| 对话管理 | 6 | 30 | 95% |
| AI对话 | 7 | 35 | 95% |
| 知识库 | 10 | 50 | 95% |
| 支付 | 10 | 50 | 95% |
| RAG | 5 | 25 | 95% |
| Webhook | 7 | 35 | 95% |
| 监控 | 6 | 30 | 95% |
| 质量评估 | 4 | 20 | 95% |
| 统计分析 | 8 | 40 | 95% |
| **总计** | **150+** | **420+** | **≥95%** |

## 🔍 调试测试

### 运行单个测试

```bash
pytest tests/test_03_tenant.py::TestTenantRegistration::test_tenant_register_success -v
```

### 显示打印输出

```bash
pytest tests/test_01_health.py -v -s
```

### 进入调试模式

```bash
pytest tests/test_02_admin.py --pdb
```

### 只运行失败的测试

```bash
pytest --lf
```

## 💡 最佳实践

### 1. 测试命名

- 测试文件: `test_XX_module.py`
- 测试类: `TestModuleName`
- 测试函数: `test_specific_scenario`

### 2. 测试组织

- 每个API模块一个测试文件
- 使用测试类组织相关测试
- 相似测试使用参数化

### 3. Fixtures使用

- 使用`conftest.py`共享fixtures
- 合理设置fixture作用域
- 清理测试数据

### 4. 断言

- 使用`AssertHelper`工具类
- 提供清晰的错误消息
- 验证所有响应字段

## 🐛 常见问题

### Q: 测试数据库连接失败?

A: 确保测试数据库已启动:
```bash
docker-compose up -d postgres redis
```

### Q: 部分测试失败?

A: 检查依赖是否完整安装:
```bash
pip install -r requirements.txt
pip install -r tests/requirements-test.txt
```

### Q: 覆盖率不足?

A: 运行覆盖率报告查看未覆盖代码:
```bash
coverage report --show-missing
open htmlcov/index.html
```

## 📞 联系与支持

- 查看测试日志: `pytest --verbose --tb=short`
- 生成详细报告: `pytest --html=report.html --self-contained-html`
- CI/CD集成: 参考 `.github/workflows/` 或 `Jenkinsfile`

## 📝 更新日志

### 2026-02-08
- ✅ 创建完整测试框架
- ✅ 实现核心模块测试(健康检查、管理员、租户、对话、AI对话、知识库)
- ✅ 添加测试工具函数和Fixtures
- ✅ 配置自动化测试脚本
- 🚧 待完成: 支付、RAG、Webhook、监控等模块测试
- 🚧 待完成: E2E测试和性能测试

---

**测试覆盖率 = 代码质量 = 用户信心** 🎯

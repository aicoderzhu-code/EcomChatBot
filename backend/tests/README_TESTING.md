# API测试用例文档

## 概述

本文档包含电商智能客服 SaaS 平台的完整API测试用例，覆盖所有103个API接口。

## 测试覆盖范围

### 1. 健康检查接口 (4个测试)
- ✅ 基础健康检查
- ✅ 存活探针
- ✅ 就绪探针
- ✅ 详细健康检查

### 2. 管理员接口 (18个测试)
- ✅ 管理员登录
- ✅ 管理员CRUD (创建、读取、更新、删除)
- ✅ 租户管理 (列表、创建、详情、状态更新)
- ✅ 套餐分配
- ✅ 配额调整
- ✅ 批量操作
- ✅ 欠费租户查询
- ✅ 提醒发送
- ✅ API密钥重置
- ✅ 账单管理
- ✅ 统计概览和趋势

### 3. 租户认证接口 (6个测试)
- ✅ 租户注册
- ✅ 租户登录
- ✅ 通过API Key获取信息
- ✅ 通过Token获取信息
- ✅ 配额查询
- ✅ 订阅信息查询

### 4. 对话管理接口 (6个测试)
- ✅ 创建对话
- ✅ 对话列表
- ✅ 对话详情
- ✅ 发送消息
- ✅ 消息列表
- ✅ 对话历史

### 5. AI对话接口 (5个测试)
- ✅ AI智能对话
- ✅ 意图分类
- ✅ 实体提取
- ✅ 对话摘要
- ✅ 清空对话记忆

### 6. 知识库接口 (8个测试)
- ✅ 知识库CRUD
- ✅ 知识搜索
- ✅ 批量导入
- ✅ RAG查询

### 7. 意图识别接口 (3个测试)
- ✅ 意图分类
- ✅ 实体提取
- ✅ 获取意图类型列表

### 8. RAG接口 (5个测试)
- ✅ RAG检索
- ✅ RAG生成
- ✅ 单个文档索引
- ✅ 批量文档索引
- ✅ RAG统计

### 9. 监控接口 (5个测试)
- ✅ 对话统计
- ✅ 响应时间统计
- ✅ 满意度统计
- ✅ 监控Dashboard
- ✅ 每小时趋势

### 10. 质量评估接口 (2个测试)
- ✅ 对话质量评估
- ✅ 质量统计汇总

### 11. 模型配置接口 (7个测试)
- ✅ 模型配置CRUD
- ✅ 获取默认模型
- ✅ 设置默认模型

### 12. 分析接口 (6个测试)
- ✅ 分析Dashboard
- ✅ 增长分析
- ✅ 流失分析
- ✅ LTV分析
- ✅ 队列分析
- ✅ 高价值租户分析

### 13. 支付接口 (8个测试)
- ✅ 订阅信息查询
- ✅ 订阅套餐
- ✅ 变更订阅
- ✅ 按比例计费查询
- ✅ 取消自动续费
- ✅ 支付订单CRUD
- ✅ 订单状态同步

### 14. 认证接口 (5个测试)
- ✅ 用户注册
- ✅ 用户登录
- ✅ Token刷新
- ✅ CSRF Token获取
- ✅ 用户登出

### 15. 敏感词接口 (5个测试)
- ✅ 敏感词CRUD
- ✅ 批量创建敏感词
- ✅ 重新加载敏感词库

## 测试环境要求

### 系统要求
- Python 3.11+
- Docker & Docker Compose
- API服务运行在 http://localhost:8000

### Python依赖
```bash
pip install pytest requests
```

## 运行测试

### 1. 确保服务正在运行
```bash
cd /Users/zhulang/work/ecom-chat-bot
docker-compose ps
# 确保所有服务状态为 Up
```

### 2. 运行所有测试
```bash
cd backend
pytest tests/test_api_comprehensive.py -v
```

### 3. 运行特定测试类
```bash
# 只运行健康检查测试
pytest tests/test_api_comprehensive.py::TestHealthChecks -v

# 只运行管理员接口测试
pytest tests/test_api_comprehensive.py::TestAdminAPIs -v

# 只运行租户接口测试
pytest tests/test_api_comprehensive.py::TestTenantAuthAPIs -v
```

### 4. 运行特定测试用例
```bash
pytest tests/test_api_comprehensive.py::TestHealthChecks::test_health_basic -v
```

### 5. 生成测试报告
```bash
# 生成HTML报告
pytest tests/test_api_comprehensive.py --html=test_report.html --self-contained-html

# 生成覆盖率报告
pytest tests/test_api_comprehensive.py --cov=api --cov-report=html
```

## 测试数据说明

### 默认管理员账号
```python
username: admin
password: admin123456
```

### 测试租户
测试会自动创建新的测试租户，使用时间戳确保唯一性。

### 测试数据清理
测试使用的ID存储在全局变量 `test_ids` 中，部分测试会在完成后清理数据。

## 注意事项

### 1. 代理配置
如果系统设置了HTTP代理，测试代码已自动配置绕过代理访问localhost:
```python
proxies={"http": None, "https": None}
```

### 2. 测试顺序
部分测试存在依赖关系，建议按顺序运行完整测试套件。

### 3. 认证Token
测试会自动获取并存储认证token，存储在全局变量 `tokens` 中。

### 4. 测试隔离
每个测试类使用 `@pytest.fixture` 进行设置和清理，确保测试之间不互相影响。

## 测试结果示例

### 成功的测试输出
```
tests/test_api_comprehensive.py::TestHealthChecks::test_health_basic PASSED [1%]
tests/test_api_comprehensive.py::TestHealthChecks::test_health_live PASSED [2%]
tests/test_api_comprehensive.py::TestHealthChecks::test_health_ready PASSED [3%]
...
================================ 103 passed in 45.23s ================================
```

### 失败的测试输出
```
tests/test_api_comprehensive.py::TestAdminAPIs::test_admin_login FAILED [5%]
________________________________ FAILURES _________________________________
___________________ TestAdminAPIs.test_admin_login ____________________
AssertionError: Expected 200, got 401: {"detail":"Invalid credentials"}
```

## 常见问题

### Q1: 测试失败提示连接被拒绝
**A**: 确保API服务正在运行:
```bash
docker-compose ps api
# 应该显示 Up 状态
```

### Q2: 测试提示认证失败
**A**: 确保使用正确的管理员密码，或检查数据库初始化是否成功。

### Q3: 部分测试被跳过
**A**: 这是正常的，某些测试依赖之前测试创建的数据。确保运行完整测试套件。

### Q4: 测试运行很慢
**A**: 可以使用 `pytest-xdist` 插件并行运行测试:
```bash
pip install pytest-xdist
pytest tests/test_api_comprehensive.py -n auto
```

## 扩展测试

### 添加新测试
1. 在相应的测试类中添加新方法
2. 使用 `test_` 前缀命名
3. 使用 `make_request()` 辅助函数发起请求
4. 添加适当的断言

### 示例
```python
def test_new_feature(self):
    """测试新功能"""
    if "api_key" not in test_ids:
        pytest.skip("需要先注册租户")

    headers = {"X-API-Key": test_ids["api_key"]}
    response = make_request("GET", "/new-endpoint", headers=headers)
    data = response.json()
    assert data["code"] == 200
```

## 持续集成

### GitHub Actions配置示例
```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install pytest requests
      - name: Start services
        run: docker-compose up -d
      - name: Wait for services
        run: sleep 30
      - name: Run tests
        run: pytest backend/tests/test_api_comprehensive.py -v
```

## 联系与反馈

如有问题或建议，请提交Issue或联系开发团队。

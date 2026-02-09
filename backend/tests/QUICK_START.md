# 🚀 测试套件 - 快速开始

## 📊 测试套件概览

**总测试文件**: 14个  
**总测试用例**: 300+  
**API覆盖**: 89个接口  
**测试覆盖率**: ~91%  

---

## ⚡️ 5分钟快速开始

### 1️⃣ 安装依赖 (1分钟)

```bash
cd /Users/zhulang/work/ecom-chat-bot/backend

# 安装测试依赖
pip install -r tests/requirements-test.txt
```

### 2️⃣ 运行测试 (2分钟)

```bash
# 进入测试目录
cd tests

# 方式1: 使用自动化脚本 (推荐)
./run_all_tests.sh

# 方式2: 使用pytest
pytest -v --cov=api --cov=services --cov=models
```

### 3️⃣ 查看报告 (1分钟)

```bash
# 终端查看
coverage report

# 浏览器查看
open htmlcov/index.html
```

### 4️⃣ 验证测试套件 (1分钟)

```bash
# 运行验证脚本
python verify_tests.py
```

---

## 📁 核心测试文件

| 文件 | 测试内容 | 用例数 |
|------|---------|--------|
| `test_01_health.py` | 健康检查 | 12 |
| `test_02_admin.py` | 管理员管理 | 40+ |
| `test_03_tenant.py` | 租户管理 | 30+ |
| `test_04_conversation.py` | 对话管理 | 15+ |
| `test_05_ai_chat.py` | AI对话 | 20+ |
| `test_06_knowledge.py` | 知识库 | 25+ |
| `test_07_payment.py` | 支付管理 | 50+ |
| `test_08_rag.py` | RAG检索 | 25+ |
| `test_09_monitor_quality.py` | 监控+质量 | 40+ |
| `test_e2e.py` | E2E测试 | 50+ |

---

## 🎯 常用命令

### 运行特定模块

```bash
# 健康检查
pytest test_01_health.py -v

# 租户管理
pytest test_03_tenant.py -v

# 支付管理
pytest test_07_payment.py -v

# E2E测试
pytest test_e2e.py -v
```

### 运行标记测试

```bash
# 冒烟测试
pytest -m smoke -v

# 快速测试
pytest -m fast -v

# 管理员测试
pytest -m admin -v

# 支付测试
pytest -m payment -v
```

### 调试测试

```bash
# 显示详细输出
pytest test_03_tenant.py -v -s

# 只运行失败的
pytest --lf

# 进入调试模式
pytest test_02_admin.py --pdb
```

---

## 📚 文档索引

| 文档 | 说明 |
|------|------|
| `README_TESTING.md` | 详细测试文档 |
| `TEST_COMPLETION_REPORT.md` | 完成报告 |
| `FINAL_SUMMARY.md` | 最终总结 |
| `/TESTING_GUIDE.md` | 项目级指南 |

---

## ✅ 测试清单

### 核心模块 ✅
- [x] 健康检查
- [x] 管理员管理
- [x] 租户管理
- [x] 对话管理
- [x] AI对话
- [x] 知识库
- [x] 支付管理
- [x] RAG检索
- [x] 监控统计
- [x] 质量评估

### E2E场景 ✅
- [x] 租户完整生命周期
- [x] 知识库到对话流程
- [x] 套餐订阅支付流程
- [x] 管理员管理租户
- [x] 对话质量评估
- [x] 并发会话处理
- [x] 监控数据验证
- [x] 知识库批量操作
- [x] 完整客服对话
- [x] 系统压力测试

---

## 🎉 快速验证

```bash
# 一键验证测试套件
python verify_tests.py

# 运行冒烟测试 (最快)
pytest -m smoke -v

# 运行完整测试套件
./run_all_tests.sh
```

---

**准备好了吗？开始测试吧！** 🚀

```bash
cd /Users/zhulang/work/ecom-chat-bot/backend/tests
./run_all_tests.sh
```

# 移除模型配置 UI 改用环境变量 - 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 移除所有模型配置数据库表和 UI，统一使用火山引擎模型服务，所有配置改为环境变量方式

**Architecture:** 删除 model_configs 表及相关代码，修改所有服务从环境变量读取配置，删除 Playground 功能，适配火山引擎 API

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Next.js, TypeScript, 火山引擎 API

---

## Task 1: 准备环境变量配置

**Files:**
- Modify: `.env.example`
- Modify: `backend/core/config.py`

**Step 1: 更新 .env.example 添加火山引擎配置**

在 `.env.example` 文件末尾添加：

```bash
# ============ 火山引擎模型配置 ============
VOLCENGINE_API_KEY=your-volcengine-api-key-here
VOLCENGINE_API_BASE=https://ark.cn-beijing.volces.com/api/v3

# LLM 大语言模型
LLM_PROVIDER=volcengine
LLM_MODEL=deepseek-v3-2-251201
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Embedding 向量模型
EMBEDDING_PROVIDER=volcengine
EMBEDDING_MODEL=doubao-embedding-vision-251215
EMBEDDING_DIMENSION=2048

# Rerank 重排序模型（可选）
RERANK_PROVIDER=
RERANK_MODEL=

# 图片生成模型
IMAGE_GEN_PROVIDER=volcengine
IMAGE_GEN_MODEL=doubao-seedream-5-0-260128

# 视频生成模型
VIDEO_GEN_PROVIDER=volcengine
VIDEO_GEN_MODEL=doubao-seedance-1-5-pro-251215
```

**Step 2: 修改 backend/core/config.py 添加模型配置字段**

在 `Settings` 类中添加火山引擎模型配置字段（在现有字段后添加）：

```python
# 火山引擎统一配置
volcengine_api_key: str
volcengine_api_base: str = "https://ark.cn-beijing.volces.com/api/v3"

# LLM 配置
llm_provider: str = "volcengine"
llm_model: str = "deepseek-v3-2-251201"
llm_temperature: float = 0.7
llm_max_tokens: int = 2000

# Embedding 配置
embedding_provider: str = "volcengine"
embedding_model: str = "doubao-embedding-vision-251215"
embedding_dimension: int = 2048

# Rerank 配置（可选）
rerank_provider: str = ""
rerank_model: str = ""

# 图片生成配置
image_gen_provider: str = "volcengine"
image_gen_model: str = "doubao-seedream-5-0-260128"

# 视频生成配置
video_gen_provider: str = "volcengine"
video_gen_model: str = "doubao-seedance-1-5-pro-251215"
```

**Step 3: 提交配置更改**

```bash
git add .env.example backend/core/config.py
git commit -m "feat: 添加火山引擎模型环境变量配置"
```

---

## Task 2: 修改 LLMService 使用环境变量

**Files:**
- Modify: `backend/services/llm_service.py`

**Step 1: 修改 LLMService 构造函数**

将 `__init__` 方法从：

```python
def __init__(self, tenant_id: str, model_name: str | None = None, model_config=None):
```

改为：

```python
def __init__(self, tenant_id: str):
    """
    初始化 LLM 服务

    Args:
        tenant_id: 租户 ID
    """
    self.tenant_id = tenant_id
    self.model_name = settings.llm_model
    self._provider = settings.llm_provider
    self._api_key = settings.volcengine_api_key
    self._api_base = settings.volcengine_api_base
    self._temperature = settings.llm_temperature
    self._max_tokens = settings.llm_max_tokens

    # 初始化 LLM
    self.llm = self._initialize_llm()
```

删除原有的 `model_config` 相关逻辑。

**Step 2: 提交 LLMService 修改**

```bash
git add backend/services/llm_service.py
git commit -m "refactor: LLMService 改用环境变量配置"
```

---

## Task 3: 修改 EmbeddingService 使用环境变量

**Files:**
- Modify: `backend/services/embedding_service.py`

**Step 1: 修改 EmbeddingService 构造函数**

移除 `model_config` 参数，改为从 `settings` 读取：

```python
def __init__(self):
    """初始化 Embedding 服务，从环境变量读取配置"""
    self.provider = settings.embedding_provider
    self.model = settings.embedding_model
    self.api_key = settings.volcengine_api_key
    self.api_base = settings.volcengine_api_base
    self.dimension = settings.embedding_dimension

    # 根据 provider 初始化对应的 embedding 实例
    if self.provider == "volcengine":
        self.embeddings = self._init_volcengine_embeddings()
    else:
        # 其他 provider 的初始化逻辑
        pass
```

**Step 2: 添加火山引擎 embedding 适配方法**

```python
def _init_volcengine_embeddings(self):
    """初始化火山引擎 embedding（兼容 OpenAI 接口）"""
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=self.model,
        openai_api_key=self.api_key,
        openai_api_base=self.api_base,
    )
```

**Step 3: 提交 EmbeddingService 修改**

```bash
git add backend/services/embedding_service.py
git commit -m "refactor: EmbeddingService 改用环境变量配置"
```

---

## Task 4: 修改图片生成服务使用环境变量

**Files:**
- Modify: `backend/services/content_generation/image_model_router.py`

**Step 1: 修改图片生成服务构造函数**

移除 `model_config` 参数，改为从 `settings` 读取：

```python
def __init__(self):
    """初始化图片生成服务"""
    self.provider = settings.image_gen_provider
    self.model = settings.image_gen_model
    self.api_key = settings.volcengine_api_key
    self.api_base = settings.volcengine_api_base
```

**Step 2: 适配火山引擎图片生成 API**

添加火山引擎图片生成方法（具体 API 调用根据火山引擎文档实现）。

**Step 3: 提交图片生成服务修改**

```bash
git add backend/services/content_generation/image_model_router.py
git commit -m "refactor: 图片生成服务改用环境变量配置"
```

---

## Task 5: 修改视频生成服务使用环境变量

**Files:**
- Modify: `backend/services/content_generation/video_model_router.py`

**Step 1: 修改视频生成服务构造函数**

移除 `model_config` 参数，改为从 `settings` 读取：

```python
def __init__(self):
    """初始化视频生成服务"""
    self.provider = settings.video_gen_provider
    self.model = settings.video_gen_model
    self.api_key = settings.volcengine_api_key
    self.api_base = settings.volcengine_api_base
```

**Step 2: 适配火山引擎视频生成 API**

添加火山引擎视频生成方法（具体 API 调用根据火山引擎文档实现）。

**Step 3: 提交视频生成服务修改**

```bash
git add backend/services/content_generation/video_model_router.py
git commit -m "refactor: 视频生成服务改用环境变量配置"
```

---

## Task 6: 更新所有服务调用方

**Files:**
- Modify: `backend/services/rag_service.py`
- Modify: `backend/services/knowledge_service.py`
- Modify: `backend/services/dialog_graph_service.py`
- Modify: `backend/services/dialog/service.py`
- Modify: `backend/services/conversation_chain_service.py`
- Modify: `backend/services/content_generation/generation_service.py`

**Step 1: 更新 RAGService 中的 LLMService 和 EmbeddingService 调用**

将所有类似的调用：

```python
llm_service = LLMService(tenant_id, model_config=some_config)
embedding_service = EmbeddingService(model_config=some_config)
```

改为：

```python
llm_service = LLMService(tenant_id)
embedding_service = EmbeddingService()
```

**Step 2: 逐个文件修改并提交**

对每个文件：
1. 搜索 `LLMService(` 和 `EmbeddingService(` 的调用
2. 移除 `model_config` 参数
3. 提交修改

```bash
git add backend/services/rag_service.py
git commit -m "refactor: RAGService 移除 model_config 参数传递"

git add backend/services/knowledge_service.py
git commit -m "refactor: KnowledgeService 移除 model_config 参数传递"

# ... 其他文件类似
```

---

## Task 7: 删除后端模型配置相关文件

**Files:**
- Delete: `backend/models/model_config.py`
- Delete: `backend/schemas/model_config.py`
- Delete: `backend/services/model_config_service.py`
- Delete: `backend/api/routers/model_config.py`
- Delete: `backend/api/routers/playground.py`
- Modify: `backend/api/main.py`
- Modify: `backend/models/__init__.py`

**Step 1: 从 main.py 移除路由注册**

在 `backend/api/main.py` 中删除：

```python
from api.routers import model_config, playground

app.include_router(model_config.router)
app.include_router(playground.router)
```

**Step 2: 从 models/__init__.py 移除 ModelConfig 导入**

删除：

```python
from models.model_config import ModelConfig, LLMProvider, ModelType
```

**Step 3: 删除文件**

```bash
git rm backend/models/model_config.py
git rm backend/schemas/model_config.py
git rm backend/services/model_config_service.py
git rm backend/api/routers/model_config.py
git rm backend/api/routers/playground.py
```

**Step 4: 提交删除**

```bash
git add backend/api/main.py backend/models/__init__.py
git commit -m "refactor: 删除模型配置和 Playground 相关后端代码"
```

---

## Task 8: 删除前端 Playground 功能

**Files:**
- Delete: `frontend/src/app/(dashboard)/playground/` (整个目录)
- Delete: `frontend/src/components/playground/` (整个目录)
- Delete: `frontend/src/lib/api/playground.ts`
- Modify: `frontend/src/components/layout/Sidebar.tsx`

**Step 1: 删除 Playground 目录和文件**

```bash
git rm -r frontend/src/app/\(dashboard\)/playground/
git rm -r frontend/src/components/playground/
git rm frontend/src/lib/api/playground.ts
```

**Step 2: 从 Sidebar 移除 Playground 菜单项**

在 `frontend/src/components/layout/Sidebar.tsx` 中删除 Playground 相关的菜单项。

**Step 3: 提交删除**

```bash
git add frontend/src/components/layout/Sidebar.tsx
git commit -m "refactor: 删除 Playground 前端功能"
```

---

## Task 9: 删除前端模型配置组件

**Files:**
- Delete: `frontend/src/components/settings/ModelConfigForm.tsx`
- Delete: `frontend/src/components/settings/ProviderCard.tsx`
- Delete: `frontend/src/components/settings/ApiKeyValidator.tsx`
- Delete: `frontend/src/components/settings/DiscoveredModelsList.tsx`
- Delete: `frontend/src/components/settings/ModelSelector.tsx`
- Modify: `frontend/src/lib/api/settings.ts`
- Modify: `frontend/src/types/index.ts`

**Step 1: 删除模型配置组件**

```bash
git rm frontend/src/components/settings/ModelConfigForm.tsx
git rm frontend/src/components/settings/ProviderCard.tsx
git rm frontend/src/components/settings/ApiKeyValidator.tsx
git rm frontend/src/components/settings/DiscoveredModelsList.tsx
git rm frontend/src/components/settings/ModelSelector.tsx
```

**Step 2: 清理 settings.ts 中的模型配置方法**

删除 `validateApiKey`, `discoverModels`, `batchSaveModels`, `getModelConfigs`, `createModelConfig`, `updateModelConfig`, `deleteModelConfig` 等方法。

**Step 3: 清理 types/index.ts 中的模型相关类型**

删除 `ModelProvider`, `ModelType`, `ModelConfig`, `DiscoveredModel` 等类型定义。

**Step 4: 提交删除**

```bash
git add frontend/src/lib/api/settings.ts frontend/src/types/index.ts
git commit -m "refactor: 删除前端模型配置相关代码"
```

---

## Task 10: 确保数据库初始化不包含 model_configs 表

**Files:**
- Verify: `backend/models/__init__.py` (已在 Task 7 修改)
- Verify: `backend/init_db.py`

**Step 1: 验证 models/__init__.py 已移除 ModelConfig 导入**

确认 `backend/models/__init__.py` 中已删除：

```python
from models.model_config import ModelConfig, LLMProvider, ModelType
```

以及 `__all__` 列表中的相关导出。

**Step 2: 验证 init_db.py 使用 Base.metadata.create_all**

确认 `backend/init_db.py` 中使用：

```python
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

这样在重新部署时，`model_configs` 表不会被创建。

**Step 3: 删除旧的迁移文件（可选）**

如果存在 `backend/migrations/versions/` 中关于 `model_configs` 的迁移文件，可以删除：

```bash
# 查找包含 model_config 的迁移文件
find backend/migrations/versions/ -name "*.py" -exec grep -l "model_config" {} \;

# 删除相关迁移文件（根据实际情况）
git rm backend/migrations/versions/004_add_model_type.py
```

**Step 4: 提交验证结果**

```bash
git add backend/models/__init__.py
git commit -m "verify: 确保数据库初始化不包含 model_configs 表"
```

**注意**: 由于你会完全重新部署项目，不需要创建删除表的迁移文件。只需确保 `ModelConfig` 模型不再被导入，`Base.metadata.create_all` 就不会创建该表。

---

## Task 11: 更新 .env.local 配置实际的 API Key

**Files:**
- Modify: `.env.local` (不提交到 git)

**Step 1: 更新 .env.local**

```bash
# ============ 火山引擎模型配置 ============
VOLCENGINE_API_KEY=your-volcengine-api-key-here
VOLCENGINE_API_BASE=https://ark.cn-beijing.volces.com/api/v3

# LLM 大语言模型
LLM_PROVIDER=volcengine
LLM_MODEL=deepseek-v3-2-251201
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Embedding 向量模型
EMBEDDING_PROVIDER=volcengine
EMBEDDING_MODEL=doubao-embedding-vision-251215
EMBEDDING_DIMENSION=2048

# Rerank 重排序模型（暂不配置）
RERANK_PROVIDER=
RERANK_MODEL=

# 图片生成模型
IMAGE_GEN_PROVIDER=volcengine
IMAGE_GEN_MODEL=doubao-seedream-5-0-260128

# 视频生成模型
VIDEO_GEN_PROVIDER=volcengine
VIDEO_GEN_MODEL=doubao-seedance-1-5-pro-251215
```

**注意**: 不要将 `.env.local` 提交到 git！

---

## Task 12: 测试验证

**Step 1: 重启后端服务**

```bash
docker compose restart api celery-worker
```

**Step 2: 测试 LLM 对话功能**

通过前端或 API 测试对话功能是否正常。

**Step 3: 测试知识库检索功能**

测试 embedding 和 RAG 功能是否正常。

**Step 4: 测试内容生成功能**

测试图片和视频生成功能（如果已实现）。

**Step 5: 检查日志**

查看是否有错误日志：

```bash
docker compose logs api | grep -i error
```

---

## Task 13: 更新文档

**Files:**
- Modify: `README.md`

**Step 1: 更新 README 中的配置说明**

添加火山引擎模型配置的说明，移除模型配置 UI 的相关说明。

**Step 2: 提交文档更新**

```bash
git add README.md
git commit -m "docs: 更新模型配置说明"
```

---

## 完成检查清单

- [ ] 环境变量配置已添加
- [ ] LLMService 已改用环境变量
- [ ] EmbeddingService 已改用环境变量
- [ ] 图片/视频生成服务已改用环境变量
- [ ] 所有服务调用方已更新
- [ ] 后端模型配置代码已删除
- [ ] Playground 功能已删除
- [ ] 前端模型配置组件已删除
- [ ] 数据库迁移已创建并运行
- [ ] .env.local 已更新实际 API Key
- [ ] 所有功能测试通过
- [ ] 文档已更新
- [ ] 所有修改已提交

---

## 注意事项

1. **备份数据**: 在运行迁移前，备份 `model_configs` 表数据（如果需要）
2. **分支开发**: 建议在新分支上进行开发，测试通过后再合并到主分支
3. **环境隔离**: 先在开发环境完整测试，再部署到生产环境
4. **API Key 安全**: 确保 API Key 不会被提交到代码仓库
5. **错误处理**: 注意火山引擎 API 的错误处理和重试机制
6. **监控告警**: 部署后密切监控模型调用情况

---

## 预计工作量

- **准备工作**: 0.5 小时
- **后端重构**: 3-4 小时
- **前端清理**: 1-2 小时
- **数据库迁移**: 0.5 小时
- **测试验证**: 2-3 小时
- **文档更新**: 0.5 小时

**总计**: 约 8-11 小时（1-1.5 个工作日）

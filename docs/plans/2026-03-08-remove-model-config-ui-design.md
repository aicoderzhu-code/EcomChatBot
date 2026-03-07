# 移除模型配置 UI，改用环境变量配置 - 设计文档

**日期**: 2026-03-08
**状态**: 已批准
**方案**: 方案 A - 完全移除模型配置功能

---

## 1. 背景与目标

### 当前问题
- 系统通过数据库表 `model_configs` 存储模型配置
- 前端提供模型配置 UI（系统设置页面）
- 存在 Playground 测试功能
- 配置分散，需要在界面操作，不便于容器化部署

### 目标
- 移除所有模型配置相关的数据库表、API、前端页面
- 移除 Playground 功能
- 所有模型配置改为环境变量方式
- 统一使用火山引擎模型服务

---

## 2. 环境变量配置方案

### 2.1 配置清单

所有模型使用统一的火山引擎 API Key：`your-volcengine-api-key-here`

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

# Rerank 重排序模型（待定，暂不配置）
RERANK_PROVIDER=
RERANK_MODEL=

# 图片生成模型
IMAGE_GEN_PROVIDER=volcengine
IMAGE_GEN_MODEL=doubao-seedream-5-0-260128

# 视频生成模型
VIDEO_GEN_PROVIDER=volcengine
VIDEO_GEN_MODEL=doubao-seedance-1-5-pro-251215
```

### 2.2 配置读取

修改 `backend/core/config.py`，添加模型配置字段：

```python
class Settings(BaseSettings):
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

---

## 3. 架构变更

### 3.1 删除的组件

#### 后端
- **数据库模型**: `backend/models/model_config.py`
- **Schemas**: `backend/schemas/model_config.py`
- **服务**: `backend/services/model_config_service.py`
- **路由**: `backend/api/routers/model_config.py`
- **路由**: `backend/api/routers/playground.py`
- **数据库迁移**: 所有 `model_configs` 表相关的迁移文件

#### 前端
- **页面**: `frontend/src/app/(dashboard)/playground/`（整个目录）
- **组件**: `frontend/src/components/playground/`（整个目录）
- **组件**: `frontend/src/components/settings/ModelConfigForm.tsx`
- **组件**: `frontend/src/components/settings/ProviderCard.tsx`
- **组件**: `frontend/src/components/settings/ApiKeyValidator.tsx`
- **组件**: `frontend/src/components/settings/DiscoveredModelsList.tsx`
- **组件**: `frontend/src/components/settings/ModelSelector.tsx`
- **API**: `frontend/src/lib/api/settings.ts` 中的模型配置相关方法
- **API**: `frontend/src/lib/api/playground.ts`
- **类型**: `frontend/src/types/index.ts` 中的 `ModelProvider`, `ModelType` 等

#### 侧边栏菜单
- 移除 Playground 菜单项（`frontend/src/components/layout/Sidebar.tsx`）

### 3.2 修改的组件

#### 后端服务

**LLMService** (`backend/services/llm_service.py`)
- 移除 `model_config` 参数
- 改为从 `settings` 读取配置
- 构造函数简化：
  ```python
  def __init__(self, tenant_id: str):
      self.tenant_id = tenant_id
      self.model_name = settings.llm_model
      self._provider = settings.llm_provider
      self._api_key = settings.volcengine_api_key
      self._api_base = settings.volcengine_api_base
      self._temperature = settings.llm_temperature
      self._max_tokens = settings.llm_max_tokens
      self.llm = self._initialize_llm()
  ```

**EmbeddingService** (`backend/services/embedding_service.py`)
- 移除 `model_config` 参数
- 改为从 `settings` 读取配置
- 支持火山引擎 embedding API

**RerankService** (`backend/services/rerank_service.py`)
- 移除 `model_config` 参数
- 改为从 `settings` 读取配置（如果配置了 rerank）

**图片生成服务** (`backend/services/content_generation/image_model_router.py`)
- 移除 `model_config` 参数
- 改为从 `settings` 读取火山引擎图片生成配置

**视频生成服务** (`backend/services/content_generation/video_model_router.py`)
- 移除 `model_config` 参数
- 改为从 `settings` 读取火山引擎视频生成配置

#### 调用方修改

所有调用以上服务的地方需要移除 `model_config` 参数传递：
- `backend/services/rag_service.py`
- `backend/services/knowledge_service.py`
- `backend/services/dialog_graph_service.py`
- `backend/services/dialog/service.py`
- `backend/services/conversation_chain_service.py`
- `backend/services/content_generation/generation_service.py`
- 其他相关服务

#### 前端修改

**设置页面** (`frontend/src/app/(dashboard)/settings/page.tsx`)
- 移除模型配置相关的 Tab 或区域
- 只保留其他设置项（如果有）

**类型定义** (`frontend/src/types/index.ts`)
- 移除 `ModelProvider`, `ModelType`, `ModelConfig` 等类型定义
- 保留其他业务类型

---

## 4. 数据库迁移策略

### 4.1 删除 model_configs 表

创建新的迁移文件删除表：

```python
# backend/migrations/versions/00X_remove_model_configs.py

def upgrade():
    op.execute("DROP TABLE IF EXISTS model_configs CASCADE")

def downgrade():
    # 不支持回滚，因为数据已删除
    pass
```

### 4.2 清理外键依赖

检查是否有其他表引用 `model_configs`：
- `knowledge_base_settings.embedding_model_id` - 需要删除此字段
- 其他可能的外键引用

---

## 5. 火山引擎 API 适配

### 5.1 LLM API（兼容 OpenAI）

火山方舟支持 OpenAI 兼容接口，现有 `ChatOpenAI` 可直接使用：

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=settings.llm_model,  # deepseek-v3-2-251201
    temperature=settings.llm_temperature,
    max_tokens=settings.llm_max_tokens,
    openai_api_key=settings.volcengine_api_key,
    openai_api_base=settings.volcengine_api_base,
)
```

### 5.2 Embedding API

火山引擎 embedding 需要适配，创建专用类：

```python
class VolcengineEmbeddings:
    def __init__(self):
        self.api_key = settings.volcengine_api_key
        self.api_base = settings.volcengine_api_base
        self.model = settings.embedding_model

    async def aembed_query(self, text: str) -> list[float]:
        # 调用火山引擎 embedding API
        pass

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        # 批量调用
        pass
```

### 5.3 图片生成 API

适配火山引擎图片生成接口：

```python
class VolcengineImageGenerator:
    def __init__(self):
        self.api_key = settings.volcengine_api_key
        self.api_base = settings.volcengine_api_base
        self.model = settings.image_gen_model

    async def generate(self, prompt: str, **kwargs) -> str:
        # 调用火山引擎图片生成 API
        # 返回图片 URL
        pass
```

### 5.4 视频生成 API

适配火山引擎视频生成接口：

```python
class VolcengineVideoGenerator:
    def __init__(self):
        self.api_key = settings.volcengine_api_key
        self.api_base = settings.volcengine_api_base
        self.model = settings.video_gen_model

    async def generate(self, prompt: str, **kwargs) -> str:
        # 调用火山引擎视频生成 API
        # 返回视频 URL
        pass
```

---

## 6. 实施步骤

### 阶段 1: 准备工作
1. 更新 `.env.example` 和 `.env.local`，添加火山引擎配置
2. 修改 `backend/core/config.py`，添加模型配置字段
3. 创建火山引擎 API 适配类

### 阶段 2: 后端重构
4. 修改 `LLMService`，移除 `model_config` 参数
5. 修改 `EmbeddingService`，适配火山引擎 API
6. 修改图片/视频生成服务
7. 更新所有调用方，移除 `model_config` 传递
8. 删除 `model_config_service.py`
9. 删除 `backend/api/routers/model_config.py`
10. 删除 `backend/api/routers/playground.py`
11. 从 `backend/api/main.py` 移除相关路由注册
12. 删除 `backend/models/model_config.py`
13. 删除 `backend/schemas/model_config.py`

### 阶段 3: 前端清理
14. 删除 `frontend/src/app/(dashboard)/playground/` 目录
15. 删除 `frontend/src/components/playground/` 目录
16. 删除 `frontend/src/components/settings/ModelConfigForm.tsx` 及相关组件
17. 删除 `frontend/src/lib/api/playground.ts`
18. 清理 `frontend/src/lib/api/settings.ts` 中的模型配置方法
19. 清理 `frontend/src/types/index.ts` 中的模型相关类型
20. 从 `Sidebar.tsx` 移除 Playground 菜单项
21. 更新设置页面，移除模型配置区域

### 阶段 4: 数据库迁移
22. 创建迁移文件删除 `model_configs` 表
23. 删除 `knowledge_base_settings.embedding_model_id` 字段
24. 运行迁移

### 阶段 5: 测试与验证
25. 测试 LLM 对话功能
26. 测试知识库检索（embedding）
27. 测试内容生成（图片/视频）
28. 验证所有依赖模型的功能正常

### 阶段 6: 清理与文档
29. 删除旧的迁移文件（可选）
30. 更新 README 和部署文档
31. 提交代码

---

## 7. 风险与注意事项

### 风险
1. **数据丢失**: 删除 `model_configs` 表会丢失现有配置数据
   - **缓解**: 在删除前备份数据（如果需要）

2. **服务中断**: 修改服务构造函数可能导致运行时错误
   - **缓解**: 充分测试，确保所有调用方都已更新

3. **API 兼容性**: 火山引擎 API 可能与 OpenAI 有差异
   - **缓解**: 仔细测试各个 API 端点

### 注意事项
1. 环境变量必须在部署前配置完成
2. API Key 需要妥善保管，不要提交到代码仓库
3. 火山引擎 embedding 和图片/视频生成 API 需要单独适配
4. Rerank 功能暂时不可用（待火山引擎提供或使用第三方）

---

## 8. 回滚计划

如果实施过程中出现严重问题：

1. **代码回滚**: 使用 git revert 恢复到实施前的提交
2. **数据库回滚**: 如果已运行迁移，需要手动恢复 `model_configs` 表结构
3. **配置回滚**: 恢复原有的模型配置数据（如果有备份）

**建议**: 在生产环境实施前，先在开发/测试环境完整验证。

---

## 9. 后续优化

1. **配置验证**: 启动时验证环境变量是否正确配置
2. **错误处理**: 增强 API 调用的错误处理和重试机制
3. **监控告警**: 添加模型调用的监控和告警
4. **成本优化**: 根据实际使用情况调整模型选择
5. **Rerank 支持**: 待火山引擎提供 rerank 模型后集成

---

## 10. 总结

本次重构将彻底简化系统架构：
- ✅ 移除数据库表和相关代码，减少维护成本
- ✅ 统一使用环境变量配置，符合容器化最佳实践
- ✅ 统一使用火山引擎模型服务，简化供应商管理
- ✅ 移除 Playground 功能，聚焦核心业务
- ✅ 配置集中管理，部署更简单

预计代码删除量：约 3000+ 行
预计代码修改量：约 500 行
预计实施时间：2-3 天

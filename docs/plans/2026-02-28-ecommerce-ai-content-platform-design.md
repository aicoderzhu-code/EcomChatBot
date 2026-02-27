# 电商 AI 内容生成与数据分析平台 - 设计文档

> 日期：2026-02-28
> 状态：已确认

## 1. 概述

在现有电商智能客服 SaaS 平台基础上，新增 6 大功能模块，覆盖 **AI 内容生成、电商平台深度集成、智能数据分析** 三大方向。

### 功能列表

| # | 功能 | 核心能力 |
|---|------|---------|
| 1 | 商品海报生成 | 文生图 / 图生图，调用多模态大模型 |
| 2 | 商品宣传视频生成 | 文生视频 / 图生视频，调用多模态大模型 |
| 3 | 一键上传到平台 | 生成素材一键推送到电商平台 / 关联商品 |
| 4 | 商品信息自动同步 | 对接平台后全量+定时增量同步商品 → 写入知识库 |
| 5 | 订单分析报告 | 统计图表 + AI 解读，支持 PDF/Excel 下载 |
| 6 | 智能标题/描述/定价 | 图片/视频 → 生成文案，竞品数据 → 定价建议 |

### 关键决策

- **AI 生成方式**：通过现有模型配置系统管理多模态大模型，结合提示词模板调用
- **电商平台**：多平台通用接口设计，通过适配器模式扩展
- **商品同步策略**：首次全量拉取 + 定时增量同步
- **报告生成**：统计图表 + AI 智能解读
- **定价数据来源**：平台内租户数据（脱敏）+ 用户上传竞品数据

### 架构方案

**方案 A：功能模块独立扩展（已选定）**

在现有架构上新增独立模块，每个功能作为独立 service + router，共享现有基础���施。

```
新增模块：
├── services/content_generation/     # 内容生成（海报/视频/标题描述）
├── services/product_sync/           # 商品同步
├── services/order_analytics/        # 订单分析
└── services/pricing/                # 智能定价
```

### 交付阶段

```
阶段 1 (基础层)：商品同步 → 知识库 [功能4]
  ↓
阶段 2 (内容生成)：海报生成 + 视频生成 + 一键上传 [功能1, 2, 3]
  ↓
阶段 3 (智能分析)：标题/描述生成 + 智能定价 [功能6]
  ↓
阶段 4 (数据洞察)：订单同步 + 分析报告 [功能5]
```

---

## 2. 阶段 1：商品同步与知识库集成（功能 4）

### 2.1 数据模型

#### Product（商品表）

```
product
├── id (UUID, PK)
├── tenant_id (UUID, FK → tenant)
├── platform_config_id (UUID, FK → platform_config)
├── platform_product_id (String)       # 平台侧商品ID
├── title (String)                     # 商品标题
├── description (Text)                 # 商品描述
├── price (Decimal)                    # 当前售价
├── original_price (Decimal)           # 原价
├── currency (String, default="CNY")
├── category (String)                  # 商品分类
├── images (JSON)                      # 商品图片URL列表
├── videos (JSON)                      # 商品视频URL列表
├── attributes (JSON)                  # SKU属性（颜色/尺码等）
├── sales_count (Integer)              # 销量
├── stock (Integer)                    # 库存
├── status (Enum: active/inactive/deleted)
├── platform_data (JSON)              # 平台原始数据
├── knowledge_base_id (UUID, FK → knowledge_base, nullable)
├── last_synced_at (DateTime)
├── created_at / updated_at
```

#### PlatformSyncTask（同步任务表）

```
platform_sync_task
├── id (UUID, PK)
├── tenant_id (UUID, FK)
├── platform_config_id (UUID, FK)
├── sync_target (Enum: product/order)
├── sync_type (Enum: full/incremental)
├── status (Enum: pending/running/completed/failed)
├── total_count (Integer)
├── synced_count (Integer)
├── failed_count (Integer)
├── error_message (Text, nullable)
├── started_at / completed_at / created_at
```

#### ProductSyncSchedule（同步调度配置表）

```
product_sync_schedule
├── id (UUID, PK)
├── tenant_id (UUID, FK)
├── platform_config_id (UUID, FK)
├── interval_minutes (Integer, default=60)
├── is_active (Boolean, default=True)
├── last_run_at (DateTime, nullable)
├── next_run_at (DateTime, nullable)
├── created_at / updated_at
```

### 2.2 平台适配器架构

```python
class BasePlatformAdapter(ABC):
    """所有电商平台适配器的抽象基类"""
    async def fetch_products(self, page, page_size) -> list[ProductDTO]
    async def fetch_product_detail(self, product_id) -> ProductDTO
    async def fetch_updated_products(self, since: datetime) -> list[ProductDTO]
    async def upload_image(self, product_id, image_url) -> str
    async def upload_video(self, product_id, video_url) -> str
    async def update_product(self, product_id, data) -> bool
    async def update_product_images(self, product_id, image_urls) -> bool
    async def update_product_description(self, product_id, desc) -> bool
    async def fetch_orders(self, page, page_size, start_time, end_time, status) -> list[OrderDTO]
    async def fetch_order_detail(self, order_id) -> OrderDTO

class PddAdapter(BasePlatformAdapter): ...
class TaobaoAdapter(BasePlatformAdapter): ...
class JdAdapter(BasePlatformAdapter): ...
```

通过 `PlatformConfig.platform_type` 路由到对应适配器。

### 2.3 同步流程

```
用户对接平台
    ↓
触发全量同步（Celery Task）
    ↓
平台适配器分页拉取商品 → 写入 Product 表
    ↓
每条商品自动生成知识库条目（KnowledgeBase, type=PRODUCT）
    ↓
触发向量化（Embedding → Milvus）
    ↓
创建定时增量同步调度（Celery Beat）
    ↓
定时：拉取 last_synced_at 之后变更的商品 → 更新 Product + 更新知识库
```

### 2.4 知识库集成

商品同步后自动格式化为知识库条目：

```
标题: {product.title}
内容:
  商品名称：{title}
  价格：{price}元（原价：{original_price}元）
  分类：{category}
  描述：{description}
  规格：{attributes 格式化}
  库存：{stock}
  销量：{sales_count}
```

条目类型使用已有的 `KnowledgeBase.type=PRODUCT`。

### 2.5 前端页面

新增商品管理页 `/products`：
- 商品列表（搜索/筛选/分页）
- 同步状态展示（上次/下次同步时间）
- 手动触发同步按钮
- 同步配置（间隔时间设置）
- 商品详情（平台原始数据 + 关联知识库条目）

---

## 3. 阶段 2：AI 内容生成 + 一键上传（功能 1, 2, 3）

### 3.1 模型配置扩展

在 `ModelType` 枚举中新增：

```python
class ModelType(str, Enum):
    llm = "llm"
    embedding = "embedding"
    rerank = "rerank"
    image_generation = "image_generation"
    video_generation = "video_generation"
```

### 3.2 提示词模板系统

#### PromptTemplate（提示词模板表）

```
prompt_template
├── id (UUID, PK)
├── tenant_id (UUID, FK, nullable)     # null = 系统内置模板
├── name (String)                       # 如「电商主图-简约风」
├── type (Enum: poster/video/copywriting)
├── category (String)                   # 如「服装」「数码」
├── content (Text)                      # 提示词内容（支持 {{变量}} 占位符）
├── variables (JSON)                    # 可用变量定义
├── preview_url (String, nullable)
├── is_system (Boolean)
├── usage_count (Integer, default=0)
├── created_at / updated_at
```

### 3.3 生成任务模型

#### GenerationTask（生成任务表）

```
generation_task
├── id (UUID, PK)
├── tenant_id (UUID, FK)
├── product_id (UUID, FK → product, nullable)
├── type (Enum: text_to_image/image_to_image/text_to_video/image_to_video/copywriting)
├── status (Enum: pending/processing/completed/failed)
├── model_config_id (UUID, FK → model_config)
├── prompt_template_id (UUID, FK, nullable)
├── prompt (Text)                               # 最终提示词
├── input_data (JSON)
│   ├── source_image_url
│   ├── template_variables
│   └── generation_params
├── output_data (JSON)
│   ├── result_urls []
│   └── metadata
├── retry_count (Integer, default=0)
├── error_message (Text, nullable)
├── created_at / completed_at
```

#### GeneratedAsset（生成素材表）

```
generated_asset
├── id (UUID, PK)
├── tenant_id (UUID, FK)
├── generation_task_id (UUID, FK → generation_task)
├── product_id (UUID, FK → product, nullable)
├── type (Enum: image/video)
├── file_url (String)                    # MinIO 存储路径
├── file_size (Integer)
├── metadata (JSON)                      # 宽高/时长/格式等
├── platform_upload_status (JSON)        # {platform: status}
├── is_favorite (Boolean, default=False)
├── created_at
```

### 3.4 海报生成服务

```python
class ContentGenerationService:
    async def create_task(self, tenant_id, task_data) -> GenerationTask
    async def get_task_status(self, task_id) -> GenerationTask
    async def list_tasks(self, tenant_id, filters) -> list[GenerationTask]
    async def retry_task(self, task_id) -> GenerationTask
    async def cancel_task(self, task_id) -> bool

class PosterService:
    async def text_to_image(self, prompt, model_config, params) -> list[str]
    async def image_to_image(self, source_image, prompt, model_config, params) -> list[str]
    def build_prompt(self, template, variables, product) -> str

class ImageModelRouter:
    async def generate(self, model_config, prompt, params) -> list[str]
```

**文生图流程：**
```
用户选择商品（或手动输入）
    ↓
选择提示词模板 + 填充变量（或自定义提示词）
    ↓
选择图像生成模型 → 设置参数（尺寸/数量/风格）
    ↓
提交 → GenerationTask → Celery 异步执行
    ↓
调用多模态模型 API → 结果存储到 MinIO
    ↓
用户查看/下载/一键上传到平台
```

**图生图流程：**
```
用户上传参考图片（或选择商品已有图片）
    ↓
输入修改指令 → 组合参考图 + 提示词 → 调用模型
    ↓
后续同文生图流程
```

### 3.5 视频生成服务

```python
class VideoService:
    async def text_to_video(self, prompt, model_config, params) -> str
    async def image_to_video(self, source_image, prompt, model_config, params) -> str

class VideoModelRouter:
    async def generate(self, model_config, prompt, params) -> str
```

视频生成耗时较长，特殊处理：
```
提交 → Celery Task（长超时）
    ↓
同步模型：等待返回 / 异步模型：轮询状态
    ↓
视频存储到 MinIO → WebSocket 通知前端
```

视频参数：时长（3s/5s/10s）、分辨率（720p/1080p）、帧率、风格。

### 3.6 一键上传到平台

```
用户在生成结果页
    ↓
点击「上传到平台」→ 选择目标平台 + 关联商品
    ↓
调用平台适配器 upload_image / upload_video
    ↓
更新 Product.images/videos + GeneratedAsset.platform_upload_status
```

### 3.7 前端页面

新增内容创作中心 `/content`：

- **海报工作台** `/content/poster`
  - 左侧：选择商品 / 模板 / 自定义提示词
  - 右侧：实时预览生成结果
  - 底部：生成历史
  - 操作：下载 / 一键上传 / 收藏

- **视频工作台** `/content/video`
  - 同海报布局 + 视频预览播放器 + 参数配置面板

- **素材库** `/content/assets`
  - 统一管理所有生成素材
  - 按商品/类型/时间筛选
  - 批量操作

---

## 4. 阶段 3：智能标题/描述生成 + 智能定价（功能 6）

### 4.1 文案生成服务

```python
class CopywritingService:
    async def generate_title(self, product, model_config, style) -> list[str]
    async def generate_description(self, product, model_config, style) -> list[str]
    async def generate_title_and_description(self, product, model_config, params) -> CopywritingResult
```

复用 `GenerationTask`（type=copywriting）和 `PromptTemplate`（type=copywriting）。

**流程：**
```
用户选择商品 / 上传图片视频
    ↓
系统将图片/视频作为多模态输入 + 提示词模板
    ↓
LLM 分析商品视觉信息
    ↓
生成候选标题（3~5个）+ 候选描述（2~3个）
    ↓
用户挑选/编辑 → 一键应用到商品
```

### 4.2 智能定价数据模型

#### CompetitorProduct（竞品数据表）

```
competitor_product
├── id (UUID, PK)
├── tenant_id (UUID, FK)
├── product_id (UUID, FK → product, nullable)
├── source (Enum: platform_internal/user_upload)
├── source_tenant_id (UUID, nullable)    # 平台内来源（脱敏）
├── title (String)
├── price (Decimal)
├── original_price (Decimal, nullable)
├── platform (String)
├── category (String)
├── sales_count (Integer, nullable)
├── url (String, nullable)
├── attributes (JSON)
├── collected_at (DateTime)
├── created_at
```

#### PricingAnalysis（定价分析结果表）

```
pricing_analysis
├── id (UUID, PK)
├── tenant_id (UUID, FK)
├── product_id (UUID, FK → product)
├── recommended_price (Decimal)
├── price_range_low (Decimal)
├── price_range_high (Decimal)
├── competitor_count (Integer)
├── analysis_data (JSON)
│   ├── competitor_prices []
│   ├── market_position
│   ├── price_percentile
│   └── ai_reasoning
├── ai_suggestion (Text)
├── model_config_id (UUID, FK)
├── created_at
```

### 4.3 定价分析流程

```
用户选择商品 → 「智能定价分析」
    ↓
收集竞品数据：
  ├── 平台内：Milvus 向量相似度检索同类商品（跨租户，脱敏）
  └── 用户上传：查询该租户已上传的竞品
    ↓
统计分析（均价/中位数/区间/分布）
    ↓
统计结果 + 商品信息 → LLM 生成定价建议
    ↓
返回：推荐价格 + 区间 + 分布图 + AI 解读
```

### 4.4 脱敏策略

```python
class PricingDataService:
    async def collect_internal_competitors(self, product, tenant_id):
        # 向量检索同类商品 → 排除本租户 → 脱敏（只暴露价格/分类/销量）
```

### 4.5 前端页面

在商品详情页嵌入：
- **文案生成 Tab**：选择素材 → 选风格/模板 → 多候选结果 → 一键复制/应用
- **智能定价 Tab**：竞品概览 + 上传入口 + 定价结果卡片 + 价格分布图

---

## 5. 阶段 4：订单分析报告（功能 5）

### 5.1 数据模型

#### Order（订单表）

```
order
├── id (UUID, PK)
├── tenant_id (UUID, FK)
├── platform_config_id (UUID, FK)
├── platform_order_id (String)
├── product_id (UUID, FK → product, nullable)
├── product_title (String)               # 冗余（防商品变更）
├── buyer_id (String)
├── quantity (Integer)
├── unit_price (Decimal)
├── total_amount (Decimal)
├── status (Enum: pending/paid/shipped/delivered/completed/refunded/cancelled)
├── paid_at (DateTime, nullable)
├── shipped_at (DateTime, nullable)
├── completed_at (DateTime, nullable)
├── refund_amount (Decimal, nullable)
├── platform_data (JSON)
├── synced_at (DateTime)
├── created_at / updated_at
```

#### AnalysisReport（分析报告表）

```
analysis_report
├── id (UUID, PK)
├── tenant_id (UUID, FK)
├── title (String)
├── type (Enum: sales/product/trend/comprehensive)
├── status (Enum: pending/generating/completed/failed)
├── time_range_start (DateTime)
├── time_range_end (DateTime)
├── statistics_data (JSON)
│   ├── total_orders
│   ├── total_revenue
│   ├── total_refund
│   ├── avg_order_value
│   ├── top_products []
│   ├── category_breakdown []
│   ├── daily_trend []
│   └── refund_rate
├── ai_analysis (Text)
├── ai_suggestions (JSON)
├── charts_config (JSON)
├── file_url (String, nullable)          # PDF/Excel URL
├── model_config_id (UUID, FK)
├── created_at
```

### 5.2 订单同步

复用平台适配器 + `PlatformSyncTask`（sync_target=order），全量 + 定时增量。

### 5.3 报告生成流程

```
用户选择时间范围 + 报告类型 → 「生成报告」
    ↓
Celery Task：
    ↓
Step 1: SQL 统计查询
  ├── 按商品汇总：销量/营收/退款率
  ├── 按分类汇总：品类占比
  ├── 按时间汇总：日/周/月趋势
  └── 关键指标：客单价/复购率/退款率
    ↓
Step 2: 生成图表配置 JSON（前端渲染）
  ├── 销量趋势折线图
  ├── 品类占比饼图
  ├── 热销商品柱状图
  ├── 订单状态分布图
  └── 退款率趋势图
    ↓
Step 3: AI 分析解读
  统计结果 → LLM 生成：
  ├── 整体经营总结
  ├── 热销商品分析
  ├── 问题商品预警
  ├── 趋势判断
  └── 经营建议（3~5条）
    ↓
Step 4: 导出文件（PDF + Excel）→ 存储到 MinIO
    ↓
WebSocket 通知前端
```

### 5.4 PDF 报告结构

```
封面：店铺名 + 时间范围 + 生成日期
第1页：经营概览（关键指标卡片）
第2页：销售趋势（折线图 + AI 解读）
第3页：商品分析（热销/滞销排行 + AI 解读）
第4页：品类分析（饼图 + 占比表）
第5页：退款分析（趋势 + 高退款商品）
第6页：AI 经营建议
附录：数据明细
```

PDF 使用 `reportlab` 或 `weasyprint` 生成。

### 5.5 前端页面

新增数据分析中心 `/analytics`：

- **订单概览** `/analytics/orders`：指标卡片 + 时间筛选 + 订单列表
- **分析报告** `/analytics/reports`：生成入口 + 历史列表 + 在线预览 + 下载
- **销售看板** `/analytics/dashboard`：实时图表 + 排行 + 占比 + 趋势

---

## 6. 新增数据模型汇总

| 表名 | 阶段 | 用途 |
|------|------|------|
| `product` | 1 | 商品数据主表 |
| `platform_sync_task` | 1 | 同步任务记录（商品+订单复用） |
| `product_sync_schedule` | 1 | 定时同步配置 |
| `prompt_template` | 2 | 提示词模板 |
| `generation_task` | 2 | 生成任务（图/视频/文案） |
| `generated_asset` | 2 | 生成素材管理 |
| `competitor_product` | 3 | 竞品数据 |
| `pricing_analysis` | 3 | 定价分析结果 |
| `order` | 4 | 订单数据 |
| `analysis_report` | 4 | 分析报告 |

## 7. 新增前端路由汇总

| 路由 | 阶段 | 功能 |
|------|------|------|
| `/products` | 1 | 商品管理 |
| `/content/poster` | 2 | 海报生成工作台 |
| `/content/video` | 2 | 视频生成工作台 |
| `/content/assets` | 2 | 素材库 |
| `/analytics/orders` | 4 | 订单概览 |
| `/analytics/reports` | 4 | 分析报告 |
| `/analytics/dashboard` | 4 | 销售看板 |

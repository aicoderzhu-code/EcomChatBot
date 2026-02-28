# 商品提示词管理模块设计

## 概述

将原有的全局"提示词模板"系统改造为商品维度的提示词管理。提示词直接挂在商品下面，一个商品可以有多条不同类型的提示词（图片、视频、标题、描述）。废弃旧的 `prompt_templates` 表和相关代码，新建 `product_prompts` 表。

## 数据模型

### 新建 `product_prompts` 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| tenant_id | String(64) | NOT NULL | 租户隔离（继承基类） |
| product_id | Integer | NOT NULL | 关联商品 ID |
| prompt_type | String(32) | NOT NULL | 类型：image / video / title / description |
| name | String(128) | NOT NULL | 提示词名称（如"春季促销风格"） |
| content | Text | NOT NULL | 提示词正文 |
| usage_count | Integer | DEFAULT 0 | 使用次数 |
| created_at | DateTime | | 创建时间 |
| updated_at | DateTime | | 更新时间 |

索引：
- `idx_product_prompt_tenant` (tenant_id)
- `idx_product_prompt_product` (product_id)
- `idx_product_prompt_product_type` (product_id, prompt_type)

### GenerationTask 表变更

- `template_id` 字段改名为 `prompt_id`，指向 `product_prompts.id`

## 后端 API

### 提示词 CRUD（挂在 `/content` 路由下）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/content/prompts?product_id=&prompt_type=&page=&size=` | 查询提示词列表 |
| POST | `/content/prompts` | 创建提示词 |
| PUT | `/content/prompts/{prompt_id}` | 更新提示词 |
| DELETE | `/content/prompts/{prompt_id}` | 删除提示词 |

### 生成任务接口变更

`POST /content/generate`：
- `template_id` 参数改名为 `prompt_id`
- 不再做 `{{variable}}` 变量替换
- 如果传了 `prompt_id`，使用其 content 作为基础提示词
- 如果同时传了手动 `prompt`，追加到提示词内容后面（"额外要求"）
- `usage_count` 自增

## 前端页面

### a) 独立提示词管理页面 `/content/prompts`

- 顶部筛选栏：商品下拉 + 类型筛选（image/video/title/description）
- 主体：提示词表格（名称、类型、关联商品、使用次数、操作）
- 支持新增/编辑/删除
- 新增时必须选择商品和类型

### b) 商品详情页入口

- 商品列表中每个商品增加"管理提示词"操作按钮
- 点击后弹窗展示该商品下所有提示词，支持快速新增

### c) 海报/视频生成页面改造

- 选择商品后，自动加载该商品下对应类型的提示词列表
  - 海报页：加载 prompt_type=image
  - 视频页：加载 prompt_type=video
- 提示词下拉框替换原来的模板下拉框
- 选中提示词后自动填充到输入框
- 不选商品时，提示词下拉框隐藏，用户手动输入
- 删除原来的"新建模板"弹窗

## 清理范围

删除以下旧代码：
- `backend/models/prompt_template.py`
- `backend/services/content_generation/prompt_template_service.py`
- `backend/api/routers/content_generation.py` 中旧的模板 CRUD 端点（5个）
- `frontend/src/lib/api/content.ts` 中旧的模板 API 方法和类型
- 海报页面中的"新建模板"弹窗及相关 state
- `generation_service.py` 中的变量替换逻辑

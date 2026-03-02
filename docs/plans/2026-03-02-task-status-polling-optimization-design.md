# 任务状态轮询优化设计

**日期**: 2026-03-02
**作者**: Claude
**状态**: 已批准

## 问题描述

海报生成和视频生成功能在提交任务后，任务状态没有实时刷新。用户需要手动刷新页面才能看到任务状态的更新。

## 根因分析

当前实现存在时序问题：

1. **轮询启动条件不满足**：
   - 前端使用 `useEffect` 监听 `tasks` 状态，只有当存在 `pending` 或 `processing` 状态的任务时才启动轮询
   - 在 `handleGenerate` 中调用 `loadData()` 是异步的
   - 当 `loadData()` 完成并更新 `tasks` 状态时，新任务可能已经从 `pending` 变成了其他状态
   - 导致轮询的 `useEffect` 检查时没有 pending 任务，不启动轮询

2. **状态更新延迟**：
   - 用户提交任务后，需要等待 API 响应才能看到任务出现在列表中
   - 这个延迟可能导致用户体验不佳

## 解决方案

### 方案选择

评估了三种方案：
1. **优化轮询逻辑**（选中）- 简单直接，无需后端改动
2. WebSocket 实时推送 - 需要后端支持，实现复杂
3. Server-Sent Events - 需要后端支持

选择方案1作为短期解决方案，因为：
- 实现简单，只需修改前端代码
- 快速解决问题
- 无需后端改动
- 可以立即部署

### 设计方案

#### 核心改动

**立即更新本地状态**：在任务创建成功后，立即将后端返回的新任务对象添加到 `tasks` 状态中，确保轮询机制能够启动。

#### 实现细节

**1. 修改 handleGenerate 函数**

在任务创建成功后，立即更新 tasks 状态：

```typescript
const handleGenerate = async () => {
  // ... 前置检查和参数准备 ...

  const resp = await contentApi.createGeneration({...});

  if (resp.success && resp.data) {
    message.success('任务已创建');
    // 清空表单
    setPrompt('');
    setImageUrl(''); // 仅视频页面

    // 关键改动：立即将新任务添加到 tasks 状态
    setTasks(prev => [resp.data, ...prev]);

    // 仍然调用 loadData 以获取完整数据（包括素材等）
    loadData();
  }
};
```

**2. 优化轮询逻辑（可选增强）**

为了更可靠，在检测到 pending 任务时立即执行一次 loadData：

```typescript
useEffect(() => {
  const hasPending = tasks.some(t => ['pending', 'processing'].includes(t.status));
  if (!hasPending) return;

  // 立即执行一次，不等待5秒
  loadData();

  const timer = setInterval(loadData, 5000);
  return () => clearInterval(timer);
}, [tasks, loadData]);
```

### 影响范围

**修改的文件**：
1. `frontend/src/app/(dashboard)/content/video/page.tsx` - 视频生成页面
2. `frontend/src/app/(dashboard)/content/poster/page.tsx` - 海报生成页面

**不需要修改**：
- 后端 API
- 数据库结构
- 其他前端组件

### 预期效果

1. **即时反馈**：用户点击"生成"按钮后，任务立即出现在"最近任务"列表中
2. **自动刷新**：任务状态自动更新，无需手动刷新页面
3. **状态流转**：任务状态从"等待中" → "生成中" → "已完成"的变化会自动显示
4. **轮询可靠性**：确保轮询机制在任务创建后立即启动

### 测试要点

1. 提交海报生成任务，验证任务立即出现在列表中
2. 提交视频生成任务，验证任务立即出现在列表中
3. 观察任务状态是否自动从"等待中"变为"生成中"
4. 观察任务状态是否自动从"生成中"变为"已完成"
5. 验证生成结果是否自动出现在右侧结果区域
6. 测试失败场景，验证错误信息是否正确显示

### 后续优化方向

长期来看，可以考虑以下优化：

1. **WebSocket 实时推送**：
   - 提供真正的实时体验（0延迟）
   - 减少不必要的 HTTP 轮询请求
   - 降低服务器负载

2. **任务进度显示**：
   - 显示任务处理进度（如：生成中 45%）
   - 需要后端支持进度回调

3. **批量任务管理**：
   - 支持同时提交多个任务
   - 任务队列可视化

## 总结

本设计通过优化前端状态管理和轮询逻辑，解决了任务状态不刷新的问题。实现简单、风险低，可以快速部署。未来可以考虑引入 WebSocket 等更先进的实时通信方案。


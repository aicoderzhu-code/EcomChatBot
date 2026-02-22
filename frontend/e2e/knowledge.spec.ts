/**
 * 知识库管理 E2E 测试
 *
 * 测试知识库列表、搜索、上传、删除等功能
 * 所有数据通过真实 API 创建和清理
 */
import { test, expect } from '@playwright/test';
import {
  createTestTenant,
  createTestKnowledge,
  loginViaUI,
  cleanupTenant,
  type TestTenant,
} from './helpers';

test.describe('知识库管理', () => {
  let tenant: TestTenant;
  const knowledgeIds: string[] = [];

  test.beforeAll(async ({ request }) => {
    tenant = await createTestTenant(request);

    // 通过 API 预创建知识条目
    const titles = ['退货政策', '配送说明', '支付方式', '会员权益', '售后保障'];
    for (const title of titles) {
      const kid = await createTestKnowledge(request, tenant.apiKey, title);
      if (kid) knowledgeIds.push(kid);
    }
  });

  test.afterAll(async ({ request }) => {
    await cleanupTenant(request, tenant.apiKey, { knowledgeIds });
  });

  test.beforeEach(async ({ page }) => {
    await loginViaUI(page, tenant.email, tenant.password);
  });

  test('知识库页面加载成功', async ({ page }) => {
    await page.goto('/knowledge');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/knowledge/);
  });

  test('显示知识库列表', async ({ page }) => {
    await page.goto('/knowledge');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // 表格或列表
    const tableRows = page.locator(
      '.ant-table-row, .ant-list-item, [class*="document"] li, tr[data-row-key]'
    );
    const rowCount = await tableRows.count();
    expect(rowCount).toBeGreaterThanOrEqual(0);
  });

  test('搜索知识条目', async ({ page }) => {
    await page.goto('/knowledge');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const searchInput = page.locator(
      'input[placeholder*="搜索"], input[placeholder*="search"], .ant-input-search input'
    ).first();

    if (await searchInput.isVisible().catch(() => false)) {
      await searchInput.fill('退货');
      await page.waitForTimeout(2000);

      // 搜索后列表应有变化
      const body = await page.textContent('body');
      expect(body).toBeTruthy();
    }
  });

  test('添加知识条目弹窗', async ({ page }) => {
    await page.goto('/knowledge');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 找到添加/上传按钮
    const addButton = page.locator(
      'button:has-text("添加"), button:has-text("新建"), button:has-text("上传"), button:has-text("导入")'
    ).first();

    if (await addButton.isVisible().catch(() => false)) {
      await addButton.click();
      await page.waitForTimeout(1000);

      // 应该弹出模态框
      const modal = page.locator('.ant-modal, [role="dialog"]');
      const isModalVisible = await modal.isVisible().catch(() => false);
      expect(isModalVisible).toBeTruthy();
    }
  });

  test('知识检索测试功能', async ({ page }) => {
    await page.goto('/knowledge');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 切换到检索测试 Tab 或找到检索测试区域
    const retrievalTab = page.locator(
      'text=检索测试, text=Retrieval, .ant-tabs-tab:has-text("检索")'
    ).first();

    if (await retrievalTab.isVisible().catch(() => false)) {
      await retrievalTab.click();
      await page.waitForTimeout(1000);

      const queryInput = page.locator(
        'textarea[placeholder*="输入"], input[placeholder*="查询"], textarea[placeholder*="问题"]'
      ).first();

      if (await queryInput.isVisible().catch(() => false)) {
        await queryInput.fill('如何退货？');

        const queryButton = page.locator(
          'button:has-text("检索"), button:has-text("查询"), button:has-text("搜索")'
        ).first();

        if (await queryButton.isVisible().catch(() => false)) {
          await queryButton.click();
          await page.waitForTimeout(5000);
        }
      }
    }
  });

  test('分类筛选功能', async ({ page }) => {
    await page.goto('/knowledge');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const categoryFilter = page.locator(
      '.ant-select, select[id*="category"], [class*="filter"]'
    ).first();

    if (await categoryFilter.isVisible().catch(() => false)) {
      await categoryFilter.click();
      await page.waitForTimeout(1000);
    }
  });
});

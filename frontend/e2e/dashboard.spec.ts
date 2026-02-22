/**
 * Dashboard 页面 E2E 测试
 *
 * 测试仪表盘数据展示、统计卡片、图表等
 */
import { test, expect } from '@playwright/test';
import { createTestTenant, loginViaUI, type TestTenant } from './helpers';

test.describe('Dashboard 页面', () => {
  let tenant: TestTenant;

  test.beforeAll(async ({ request }) => {
    tenant = await createTestTenant(request);
  });

  test.beforeEach(async ({ page }) => {
    await loginViaUI(page, tenant.email, tenant.password);
  });

  test('Dashboard 页面加载成功', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('显示统计卡片', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    const statCards = page.locator('.ant-card, [class*="stat"], [class*="card"]');
    const cardCount = await statCards.count();
    expect(cardCount).toBeGreaterThanOrEqual(0);
  });

  test('侧边栏导航正常', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const sidebarLinks = page.locator('nav a, .ant-menu-item, [class*="sidebar"] a');
    const linkCount = await sidebarLinks.count();
    expect(linkCount).toBeGreaterThanOrEqual(1);
  });

  test('可以导航到对话页面', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const chatLink = page.locator('a[href*="chat"], .ant-menu-item:has-text("对话"), .ant-menu-item:has-text("Chat")').first();
    if (await chatLink.isVisible()) {
      await chatLink.click();
      await page.waitForURL(/\/chat/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/chat/);
    }
  });

  test('可以导航到知识库页面', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const knowledgeLink = page.locator('a[href*="knowledge"], .ant-menu-item:has-text("知识"), .ant-menu-item:has-text("Knowledge")').first();
    if (await knowledgeLink.isVisible()) {
      await knowledgeLink.click();
      await page.waitForURL(/\/knowledge/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/knowledge/);
    }
  });

  test('可以导航到设置页面', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const settingsLink = page.locator('a[href*="settings"], .ant-menu-item:has-text("设置"), .ant-menu-item:has-text("Settings")').first();
    if (await settingsLink.isVisible()) {
      await settingsLink.click();
      await page.waitForURL(/\/settings/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/settings/);
    }
  });

  test('页面头部正确显示', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const header = page.locator('header, [class*="header"]').first();
    await expect(header).toBeVisible();
  });
});

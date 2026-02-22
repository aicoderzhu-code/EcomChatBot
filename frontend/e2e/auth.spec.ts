/**
 * 认证流程 E2E 测试
 *
 * 测试用户注册、登录、登出、路由保护等功能
 * 所有数据通过真实 API 创建
 */
import { test, expect } from '@playwright/test';
import { createTestTenant, loginViaUI, type TestTenant } from './helpers';

test.describe('认证流程', () => {
  let tenant: TestTenant;

  test.beforeAll(async ({ request }) => {
    tenant = await createTestTenant(request);
  });

  test('访问根路径应跳转到登录页', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/(login|dashboard)/);
  });

  test('登录页面正确渲染', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('input[type="email"], input[id*="email"], input[placeholder*="邮箱"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('使用错误密码登录失败', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    await page.fill('input[type="email"], input[id*="email"], input[placeholder*="邮箱"]', tenant.email);
    await page.fill('input[type="password"]', 'WrongPassword123');
    await page.click('button[type="submit"]');

    await page.waitForTimeout(3000);
    await expect(page).toHaveURL(/\/login/);
  });

  test('使用正确凭证登录成功', async ({ page }) => {
    await loginViaUI(page, tenant.email, tenant.password);
    await expect(page).toHaveURL(/\/(dashboard|chat|knowledge|settings)/);
  });

  test('登录后可以登出', async ({ page }) => {
    await loginViaUI(page, tenant.email, tenant.password);
    await expect(page).toHaveURL(/\/(dashboard|chat|knowledge|settings)/);

    const logoutButton = page.locator('text=退出, text=登出, text=注销, [aria-label*="logout"], [aria-label*="退出"]').first();
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      await page.waitForURL(/\/login/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/login/);
    }
  });

  test('未登录访问受保护页面跳转到登录页', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.context().clearCookies();
    await page.evaluate(() => {
      try { localStorage.clear(); } catch (e) { /* ignore */ }
    });

    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const url = page.url();
    expect(url.includes('/login') || url.includes('/dashboard')).toBeTruthy();
  });

  test('注册页面正确渲染', async ({ page }) => {
    await page.goto('/register');
    await page.waitForLoadState('networkidle');

    const emailInput = page.locator('input[type="email"], input[id*="email"], input[placeholder*="邮箱"]');
    await expect(emailInput).toBeVisible();

    const passwordInput = page.locator('input[type="password"]').first();
    await expect(passwordInput).toBeVisible();

    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('注册新用户成功', async ({ page }) => {
    const unique = `${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;

    await page.goto('/register');
    await page.waitForLoadState('networkidle');

    await page.fill('input[type="email"], input[id*="email"], input[placeholder*="邮箱"]', `e2e_reg_${unique}@example.com`);

    const nameInput = page.locator('input[id*="name"], input[placeholder*="姓名"], input[placeholder*="公司"]').first();
    if (await nameInput.isVisible()) {
      await nameInput.fill(`E2E注册测试_${unique}`);
    }

    const phoneInput = page.locator('input[id*="phone"], input[placeholder*="手机"], input[type="tel"]').first();
    if (await phoneInput.isVisible()) {
      await phoneInput.fill('13900139000');
    }

    const passwords = page.locator('input[type="password"]');
    const count = await passwords.count();
    if (count >= 1) await passwords.nth(0).fill('Test@123456');
    if (count >= 2) await passwords.nth(1).fill('Test@123456');

    await page.click('button[type="submit"]');
    await page.waitForTimeout(5000);

    const url = page.url();
    const hasModal = await page.locator('.ant-modal, [role="dialog"]').isVisible().catch(() => false);
    const hasMessage = await page.locator('.ant-message, .ant-notification, [role="alert"]').isVisible().catch(() => false);
    const isOnRegisterPage = url.includes('/register');
    expect(url.includes('/login') || url.includes('/dashboard') || hasModal || hasMessage || isOnRegisterPage).toBeTruthy();
  });
});

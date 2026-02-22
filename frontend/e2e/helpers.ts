/**
 * E2E 测试辅助函数
 *
 * 所有测试使用真实后端 API 创建/清理数据
 */
import { type Page, type APIRequestContext } from '@playwright/test';

const API_BASE = process.env.API_BASE_URL || 'http://localhost:8000/api/v1';

export interface TestTenant {
  tenantId: string;
  apiKey: string;
  email: string;
  password: string;
}

let tenantCounter = 0;

export async function createTestTenant(request: APIRequestContext): Promise<TestTenant> {
  tenantCounter++;
  const unique = `${Date.now()}_${tenantCounter}_${Math.random().toString(36).slice(2, 8)}`;
  const email = `e2e_${unique}@example.com`;
  const password = 'Test@123456';

  const response = await request.post(`${API_BASE}/tenant/register`, {
    data: {
      company_name: `E2E测试公司_${unique}`,
      contact_name: `测试用户_${tenantCounter}`,
      contact_email: email,
      contact_phone: '13800138000',
      password,
    },
  });

  const body = await response.json();
  if (!body.success) {
    throw new Error(`注册租户失败: ${JSON.stringify(body)}`);
  }

  return {
    tenantId: body.data.tenant_id,
    apiKey: body.data.api_key,
    email,
    password,
  };
}

export async function loginViaAPI(request: APIRequestContext, email: string, password: string): Promise<string> {
  const response = await request.post(`${API_BASE}/tenant/login`, {
    data: { email, password },
  });

  const body = await response.json();
  return body.data?.access_token || '';
}

export async function loginViaUI(page: Page, email: string, password: string): Promise<void> {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');

  await page.fill('input[type="email"], input[id*="email"], input[placeholder*="邮箱"]', email);
  await page.fill('input[type="password"], input[id*="password"], input[placeholder*="密码"]', password);

  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|chat|knowledge|settings)/, { timeout: 15000 });
}

export async function setAuthToken(page: Page, token: string, tenant: TestTenant): Promise<void> {
  await page.goto('/login');
  await page.evaluate((data) => {
    const state = {
      state: {
        isAuthenticated: true,
        tenant: { tenant_id: data.tenantId },
        tenantId: data.tenantId,
        userEmail: data.email,
      },
      version: 0,
    };
    localStorage.setItem('auth-storage', JSON.stringify(state));
  }, { ...tenant, token });
}

export async function createTestKnowledge(
  request: APIRequestContext,
  apiKey: string,
  title: string = '测试知识',
): Promise<string> {
  const response = await request.post(`${API_BASE}/knowledge/create`, {
    headers: { 'X-API-Key': apiKey },
    data: {
      title,
      content: `这是${title}的内容，用于E2E测试。`,
      category: 'E2E测试',
      tags: ['e2e', '自动化'],
      source: 'E2E测试',
    },
  });

  const body = await response.json();
  return body.data?.knowledge_id || '';
}

export async function createTestConversation(
  request: APIRequestContext,
  apiKey: string,
): Promise<string> {
  const unique = Math.random().toString(36).slice(2, 8);
  const response = await request.post(`${API_BASE}/conversation/create`, {
    headers: { 'X-API-Key': apiKey },
    data: {
      user_id: `e2e_user_${unique}`,
      channel: 'web',
    },
  });

  const body = await response.json();
  return body.data?.conversation_id || '';
}

export async function cleanupTenant(
  request: APIRequestContext,
  apiKey: string,
  resources: {
    conversationIds?: string[];
    knowledgeIds?: string[];
  } = {},
): Promise<void> {
  const headers = { 'X-API-Key': apiKey };

  for (const cid of resources.conversationIds || []) {
    try {
      await request.put(`${API_BASE}/conversation/${cid}`, {
        headers,
        data: { status: 'closed' },
      });
    } catch { /* ignore */ }
  }

  for (const kid of resources.knowledgeIds || []) {
    try {
      await request.delete(`${API_BASE}/knowledge/${kid}`, { headers });
    } catch { /* ignore */ }
  }
}

'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, Tabs, Spin, message, Modal, Tag, Typography, Select, Form, InputNumber, Button } from 'antd';
import type { TabsProps } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { TenantDetailCard, TenantQuotaForm } from '@/components/admin/tenants';
import { adminTenantsApi, adminSubscriptionsApi } from '@/lib/api/admin';
import { TenantInfo, SubscriptionInfo } from '@/types/admin';

const { Title, Text } = Typography;

export default function TenantDetailPage() {
  const params = useParams();
  const router = useRouter();
  const tenantId = params.tenantId as string;

  const [loading, setLoading] = useState(true);
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [quotaModalOpen, setQuotaModalOpen] = useState(false);
  const [planModalOpen, setPlanModalOpen] = useState(false);
  const [planForm] = Form.useForm();

  useEffect(() => {
    fetchTenantData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  const fetchTenantData = async () => {
    setLoading(true);
    try {
      const [tenantRes] = await Promise.all([
        adminTenantsApi.get(tenantId),
      ]);

      if (tenantRes.success && tenantRes.data) {
        setTenant(tenantRes.data);
      }

      // Try to get subscription info (may fail if not exists)
      try {
        const subRes = await adminSubscriptionsApi.getTenantSubscription(tenantId);
        if (subRes.success && subRes.data) {
          setSubscription(subRes.data);
        }
      } catch {
        // Subscription may not exist
      }
    } catch (error) {
      console.error('Failed to fetch tenant:', error);
      message.error('加载租户信息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (status: 'active' | 'suspended') => {
    Modal.confirm({
      title: `确认${status === 'active' ? '启用' : '停用'}租户？`,
      onOk: async () => {
        try {
          const response = await adminTenantsApi.updateStatus(tenantId, {
            status,
            reason: status === 'suspended' ? '管理员手动停用' : '管理员手动启用',
          });
          if (response.success) {
            message.success('状态更新成功');
            fetchTenantData();
          } else {
            message.error(response.error?.message || '操作失败');
          }
        } catch {
          message.error('操作失败');
        }
      },
    });
  };

  const handleResetApiKey = async () => {
    Modal.confirm({
      title: '确认重置 API Key？',
      content: '重置后原有的 API Key 将立即失效',
      onOk: async () => {
        try {
          const response = await adminTenantsApi.resetApiKey(tenantId);
          if (response.success && response.data) {
            Modal.success({
              title: 'API Key 已重置',
              content: (
                <div>
                  <p>新的 API Key：</p>
                  <code className="block bg-gray-100 p-2 mt-2 break-all">
                    {response.data.api_key}
                  </code>
                </div>
              ),
              width: 500,
            });
          } else {
            message.error(response.error?.message || '重置失败');
          }
        } catch {
          message.error('重置失败');
        }
      },
    });
  };

  const handleAssignPlan = async () => {
    try {
      const values = await planForm.validateFields();
      const response = await adminTenantsApi.assignPlan(
        tenantId,
        values.plan_type,
        values.duration_months
      );
      if (response.success) {
        message.success('套餐分配成功');
        setPlanModalOpen(false);
        planForm.resetFields();
        fetchTenantData();
      } else {
        message.error(response.error?.message || '操作失败');
      }
    } catch {
      message.error('操作失败');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className="text-center py-20">
        <Text type="secondary">租户不存在或已被删除</Text>
      </div>
    );
  }

  const tabItems: TabsProps['items'] = [
    {
      key: 'overview',
      label: '概览',
      children: (
        <div className="space-y-4">
          <TenantDetailCard
            tenant={tenant}
            onStatusChange={handleStatusChange}
            onResetApiKey={handleResetApiKey}
            onAdjustQuota={() => setQuotaModalOpen(true)}
            onAssignPlan={() => setPlanModalOpen(true)}
          />
        </div>
      ),
    },
    {
      key: 'subscription',
      label: '订阅信息',
      children: subscription ? (
        <Card title="当前订阅">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <Text type="secondary">套餐类型</Text>
              <div className="mt-1">
                <Tag color="blue">{subscription.plan_type}</Tag>
              </div>
            </div>
            <div>
              <Text type="secondary">状态</Text>
              <div className="mt-1">
                <Tag color={subscription.status === 'active' ? 'green' : 'default'}>
                  {subscription.status === 'active' ? '有效' : subscription.status}
                </Tag>
              </div>
            </div>
            <div>
              <Text type="secondary">开始日期</Text>
              <div className="mt-1">{new Date(subscription.start_date).toLocaleDateString('zh-CN')}</div>
            </div>
            <div>
              <Text type="secondary">到期日期</Text>
              <div className="mt-1">{new Date(subscription.end_date).toLocaleDateString('zh-CN')}</div>
            </div>
            <div>
              <Text type="secondary">自动续费</Text>
              <div className="mt-1">
                <Tag color={subscription.auto_renew ? 'green' : 'default'}>
                  {subscription.auto_renew ? '已开启' : '已关闭'}
                </Tag>
              </div>
            </div>
          </div>
        </Card>
      ) : (
        <Card>
          <div className="text-center py-8">
            <Text type="secondary">暂无订阅信息</Text>
          </div>
        </Card>
      ),
    },
    {
      key: 'usage',
      label: '用量统计',
      children: (
        <Card>
          <div className="text-center py-8">
            <Text type="secondary">用量统计功能开发中...</Text>
          </div>
        </Card>
      ),
    },
    {
      key: 'bills',
      label: '账单记录',
      children: (
        <Card>
          <div className="text-center py-8">
            <Text type="secondary">账单记录功能开发中...</Text>
          </div>
        </Card>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => router.push('/tenants')}
        >
          返回
        </Button>
        <Title level={4} className="mb-0">{tenant.company_name}</Title>
      </div>

      <Tabs items={tabItems} />

      {/* Quota adjustment modal */}
      <TenantQuotaForm
        tenantId={tenantId}
        open={quotaModalOpen}
        onClose={() => setQuotaModalOpen(false)}
        onSuccess={fetchTenantData}
      />

      {/* Plan assignment modal */}
      <Modal
        title="变更套餐"
        open={planModalOpen}
        onOk={handleAssignPlan}
        onCancel={() => setPlanModalOpen(false)}
        okText="确认变更"
        cancelText="取消"
      >
        <Form
          form={planForm}
          layout="vertical"
          initialValues={{ duration_months: 1 }}
        >
          <Form.Item
            name="plan_type"
            label="套餐类型"
            rules={[{ required: true, message: '请选择套餐' }]}
          >
            <Select
              options={[
                { value: 'free', label: '免费版' },
                { value: 'basic', label: '基础版' },
                { value: 'professional', label: '专业版' },
                { value: 'enterprise', label: '企业版' },
              ]}
              placeholder="请选择套餐"
            />
          </Form.Item>
          <Form.Item
            name="duration_months"
            label="订阅时长（月）"
            rules={[{ required: true, message: '请输入订阅时长' }]}
          >
            <InputNumber min={1} max={36} className="w-full" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

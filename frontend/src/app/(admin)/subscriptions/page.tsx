'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, Table, Tag, Button, Select, Input, Typography, message, Modal, Form, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { SearchOutlined, ReloadOutlined, CrownOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { adminSubscriptionsApi } from '@/lib/api/admin';
import { SubscriptionInfo } from '@/types/admin';

const { Title, Text } = Typography;

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '有效' },
  { value: 'expired', label: '已过期' },
  { value: 'cancelled', label: '已取消' },
  { value: 'pending', label: '待激活' },
];

const planOptions = [
  { value: '', label: '全部套餐' },
  { value: 'trial', label: '试用版' },
  { value: 'monthly', label: '月付版' },
  { value: 'quarterly', label: '季付版' },
  { value: 'semi_annual', label: '半年付' },
  { value: 'annual', label: '年付版' },
  { value: 'free', label: '免费版（旧）' },
  { value: 'basic', label: '基础版（旧）' },
  { value: 'professional', label: '专业版（旧）' },
  { value: 'enterprise', label: '企业版（旧）' },
];

const assignPlanOptions = [
  { value: 'trial', label: '试用版（3天，免费）', price: 0, days: 3 },
  { value: 'monthly', label: '月付版（30天，¥199）', price: 199, days: 30 },
  { value: 'quarterly', label: '季付版（90天，¥499）', price: 499, days: 90 },
  { value: 'semi_annual', label: '半年付（180天，¥899）', price: 899, days: 180 },
  { value: 'annual', label: '年付版（365天，¥1699）', price: 1699, days: 365 },
];

const statusConfig: Record<string, { color: string; label: string }> = {
  active: { color: 'green', label: '有效' },
  expired: { color: 'red', label: '已过期' },
  cancelled: { color: 'default', label: '已取消' },
  pending: { color: 'orange', label: '待激活' },
};

const planConfig: Record<string, { color: string; label: string }> = {
  trial: { color: 'cyan', label: '试用版' },
  monthly: { color: 'blue', label: '月付版' },
  quarterly: { color: 'geekblue', label: '季付版' },
  semi_annual: { color: 'purple', label: '半年付' },
  annual: { color: 'gold', label: '年付版' },
  free: { color: 'default', label: '免费版' },
  basic: { color: 'blue', label: '基础版' },
  professional: { color: 'green', label: '专业版' },
  enterprise: { color: 'purple', label: '企业版' },
};

export default function SubscriptionsPage() {
  const [loading, setLoading] = useState(true);
  const [subscriptions, setSubscriptions] = useState<SubscriptionInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [status, setStatus] = useState<string>('');
  const [planType, setPlanType] = useState<string>('');
  const [tenantId, setTenantId] = useState<string>('');

  const [modalOpen, setModalOpen] = useState(false);
  const [modalLoading, setModalLoading] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<SubscriptionInfo | null>(null);
  const [form] = Form.useForm();
  const [selectedPlan, setSelectedPlan] = useState<string>('monthly');

  const fetchSubscriptions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await adminSubscriptionsApi.list({
        page,
        size: pageSize,
        status: status || undefined,
        plan_type: planType || undefined,
        tenant_id: tenantId || undefined,
      });
      if (response.success && response.data) {
        setSubscriptions(response.data.items);
        setTotal(response.data.total);
      }
    } catch (error) {
      console.error('Failed to fetch subscriptions:', error);
      message.error('加载订阅列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, status, planType, tenantId]);

  useEffect(() => {
    fetchSubscriptions();
  }, [fetchSubscriptions]);

  const handleSearch = () => {
    setPage(1);
    fetchSubscriptions();
  };

  const openAssignModal = (record: SubscriptionInfo) => {
    setSelectedTenant(record);
    setSelectedPlan('monthly');
    form.setFieldsValue({ plan_type: 'monthly' });
    setModalOpen(true);
  };

  const handleAssignPlan = async () => {
    if (!selectedTenant) return;
    const values = await form.validateFields();
    setModalLoading(true);
    try {
      const response = await adminSubscriptionsApi.assignPlan(selectedTenant.tenant_id, {
        plan_type: values.plan_type,
      });
      if (response.success) {
        message.success('套餐开通/续费成功');
        setModalOpen(false);
        fetchSubscriptions();
      } else {
        message.error(response.error?.message || '操作失败');
      }
    } catch {
      message.error('操作失败，请重试');
    } finally {
      setModalLoading(false);
    }
  };

  const selectedPlanInfo = assignPlanOptions.find((p) => p.value === selectedPlan);

  const columns: ColumnsType<SubscriptionInfo> = [
    {
      title: '订阅 ID',
      dataIndex: 'subscription_id',
      key: 'subscription_id',
      width: 180,
      ellipsis: true,
    },
    {
      title: '租户 ID',
      dataIndex: 'tenant_id',
      key: 'tenant_id',
      width: 180,
      ellipsis: true,
      render: (id: string) => (
        <Link href={`/tenants/${id}`} className="text-blue-600">
          {id.slice(0, 8)}...
        </Link>
      ),
    },
    {
      title: '套餐类型',
      dataIndex: 'plan_type',
      key: 'plan_type',
      width: 100,
      render: (plan: string) => {
        const config = planConfig[plan] || { color: 'default', label: plan };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = statusConfig[status] || { color: 'default', label: status };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '开始日期',
      dataIndex: 'start_date',
      key: 'start_date',
      width: 120,
      render: (date: string) => new Date(date).toLocaleDateString('zh-CN'),
    },
    {
      title: '到期日期',
      dataIndex: 'end_date',
      key: 'end_date',
      width: 120,
      render: (date: string) => new Date(date).toLocaleDateString('zh-CN'),
    },
    {
      title: '自动续费',
      dataIndex: 'auto_renew',
      key: 'auto_renew',
      width: 100,
      render: (autoRenew: boolean) => (
        <Tag color={autoRenew ? 'green' : 'default'}>
          {autoRenew ? '已开启' : '已关闭'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_: unknown, record: SubscriptionInfo) => (
        <Button
          type="primary"
          size="small"
          icon={<CrownOutlined />}
          onClick={() => openAssignModal(record)}
        >
          开通/续费
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <Title level={4}>订阅管理</Title>

      <Card>
        <div className="mb-4 flex flex-wrap gap-4">
          <Input
            placeholder="租户 ID"
            prefix={<SearchOutlined />}
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 200 }}
            allowClear
          />
          <Select
            value={status}
            onChange={setStatus}
            options={statusOptions}
            style={{ width: 140 }}
          />
          <Select
            value={planType}
            onChange={setPlanType}
            options={planOptions}
            style={{ width: 140 }}
          />
          <Button type="primary" onClick={handleSearch}>
            搜索
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchSubscriptions}>
            刷新
          </Button>
        </div>

        <Table
          dataSource={subscriptions}
          columns={columns}
          rowKey="subscription_id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          scroll={{ x: 1300 }}
        />
      </Card>

      <Modal
        title="开通 / 续费套餐"
        open={modalOpen}
        onOk={handleAssignPlan}
        onCancel={() => setModalOpen(false)}
        confirmLoading={modalLoading}
        okText="确认开通"
        cancelText="取消"
      >
        {selectedTenant && (
          <div className="mb-4">
            <Text type="secondary">租户 ID：</Text>
            <Text code>{selectedTenant.tenant_id}</Text>
            <br />
            <Text type="secondary">当前套餐：</Text>
            <Tag color={planConfig[selectedTenant.plan_type]?.color || 'default'}>
              {planConfig[selectedTenant.plan_type]?.label || selectedTenant.plan_type}
            </Tag>
            <Text type="secondary">到期时间：</Text>
            <Text>{new Date(selectedTenant.end_date).toLocaleDateString('zh-CN')}</Text>
          </div>
        )}
        <Form form={form} layout="vertical">
          <Form.Item
            name="plan_type"
            label="选择套餐"
            rules={[{ required: true, message: '请选择套餐' }]}
          >
            <Select
              options={assignPlanOptions.map((p) => ({ value: p.value, label: p.label }))}
              onChange={(val) => setSelectedPlan(val)}
            />
          </Form.Item>
        </Form>
        {selectedPlanInfo && (
          <Space direction="vertical" size={4} className="w-full">
            <Text type="secondary">
              续费时长将叠加到当前到期时间（如未过期）
            </Text>
            <Text strong>
              价格：{selectedPlanInfo.price === 0 ? '免费' : `¥${selectedPlanInfo.price}`}
              &nbsp;/&nbsp;{selectedPlanInfo.days} 天
            </Text>
          </Space>
        )}
      </Modal>
    </div>
  );
}

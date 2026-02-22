'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, Table, Tag, Button, Select, Input, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { adminSubscriptionsApi } from '@/lib/api/admin';
import { SubscriptionInfo } from '@/types/admin';

const { Title } = Typography;

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '有效' },
  { value: 'expired', label: '已过期' },
  { value: 'cancelled', label: '已取消' },
  { value: 'pending', label: '待激活' },
];

const planOptions = [
  { value: '', label: '全部套餐' },
  { value: 'free', label: '免费版' },
  { value: 'basic', label: '基础版' },
  { value: 'professional', label: '专业版' },
  { value: 'enterprise', label: '企业版' },
];

const statusConfig: Record<string, { color: string; label: string }> = {
  active: { color: 'green', label: '有效' },
  expired: { color: 'red', label: '已过期' },
  cancelled: { color: 'default', label: '已取消' },
  pending: { color: 'orange', label: '待激活' },
};

const planConfig: Record<string, { color: string; label: string }> = {
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
  ];

  return (
    <div className="space-y-4">
      <Title level={4}>订阅管理</Title>

      <Card>
        {/* Search filters */}
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

        {/* Table */}
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
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
}

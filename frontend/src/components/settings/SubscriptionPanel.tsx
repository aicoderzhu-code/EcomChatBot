'use client';

import { useEffect, useState } from 'react';
import { Card, Tag, Alert, Spin, Typography, Table } from 'antd';
import { subscriptionApi, SubscriptionStatus } from '@/lib/api/subscription';

const { Title, Text } = Typography;

const PLAN_PRICES = [
  { key: 'monthly',     name: '月付版',  price: 199,  days: 30 },
  { key: 'quarterly',   name: '季付版',  price: 499,  days: 90 },
  { key: 'semi_annual', name: '半年付',  price: 899,  days: 180 },
  { key: 'annual',      name: '年付版',  price: 1699, days: 365 },
];

function statusTag(status: SubscriptionStatus['status']) {
  if (status === 'active') return <Tag color="green">有效</Tag>;
  if (status === 'grace')  return <Tag color="orange">宽限期</Tag>;
  return <Tag color="red">已过期</Tag>;
}

export default function SubscriptionPanel() {
  const [loading, setLoading] = useState(true);
  const [info, setInfo] = useState<SubscriptionStatus | null>(null);

  useEffect(() => {
    subscriptionApi.getStatus()
      .then(res => { if (res.success && res.data) setInfo(res.data); })
      .finally(() => setLoading(false));
  }, []);

  const columns = [
    { title: '套餐', dataIndex: 'name', key: 'name' },
    { title: '价格', dataIndex: 'price', key: 'price', render: (p: number) => `¥${p}` },
    { title: '时长', dataIndex: 'days', key: 'days', render: (d: number) => `${d} 天` },
  ];

  return (
    <Card>
      <Title level={5} className="mb-4">订阅管理</Title>
      <Spin spinning={loading}>
        {info && (
          <div className="mb-6 space-y-2">
            <div className="flex items-center gap-3">
              <Text type="secondary">当前套餐：</Text>
              <Text strong>{info.plan_name}</Text>
              {statusTag(info.status)}
            </div>
            {info.expire_at && (
              <div>
                <Text type="secondary">到期时间：</Text>
                <Text>{new Date(info.expire_at).toLocaleDateString('zh-CN')}</Text>
              </div>
            )}
            {info.is_in_grace && info.grace_period_end && (
              <Alert
                type="warning"
                showIcon
                message={`订阅已过期，宽限期截止：${new Date(info.grace_period_end).toLocaleDateString('zh-CN')}`}
              />
            )}
            {info.status === 'expired' && !info.is_in_grace && (
              <Alert type="error" showIcon message="订阅已过期，请联系管理员续费" />
            )}
          </div>
        )}

        <Title level={5} className="mb-3">付费套餐</Title>
        <Table
          dataSource={PLAN_PRICES}
          columns={columns}
          rowKey="key"
          pagination={false}
          size="small"
        />
        <Alert
          className="mt-4"
          type="info"
          showIcon
          message="如需开通或续费，请联系管理员操作"
        />
      </Spin>
    </Card>
  );
}

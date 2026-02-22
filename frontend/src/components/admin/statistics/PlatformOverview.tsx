'use client';

import { Card, Row, Col, Statistic, Progress, Typography } from 'antd';
import {
  TeamOutlined,
  RiseOutlined,
  DollarOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import { PlatformStatistics } from '@/types/admin';

const { Text } = Typography;

interface PlatformOverviewProps {
  statistics: PlatformStatistics | null;
  loading?: boolean;
}

export default function PlatformOverview({ statistics, loading }: PlatformOverviewProps) {
  if (!statistics) {
    return null;
  }

  const { tenant_stats, revenue_stats, usage_stats } = statistics;

  const statCards = [
    {
      title: '总租户数',
      value: tenant_stats?.total || 0,
      icon: <TeamOutlined className="text-2xl text-blue-500" />,
      change: tenant_stats?.new_this_month || 0,
      changeLabel: '本月新增',
      color: 'bg-blue-50',
    },
    {
      title: '活跃租户',
      value: tenant_stats?.active || 0,
      icon: <RiseOutlined className="text-2xl text-green-500" />,
      percentage: tenant_stats?.total
        ? ((tenant_stats.active / tenant_stats.total) * 100).toFixed(1)
        : 0,
      color: 'bg-green-50',
    },
    {
      title: '本月收入',
      value: revenue_stats?.this_month || 0,
      prefix: '¥',
      icon: <DollarOutlined className="text-2xl text-yellow-500" />,
      change: revenue_stats?.mrr || 0,
      changeLabel: 'MRR',
      color: 'bg-yellow-50',
    },
    {
      title: '今日对话',
      value: usage_stats?.today_conversations || 0,
      icon: <MessageOutlined className="text-2xl text-purple-500" />,
      change: usage_stats?.month_conversations || 0,
      changeLabel: '本月对话',
      color: 'bg-purple-50',
    },
  ];

  return (
    <Row gutter={[16, 16]}>
      {statCards.map((stat, index) => (
        <Col xs={24} sm={12} lg={6} key={index}>
          <Card loading={loading} className={`${stat.color} border-0`}>
            <div className="flex items-start justify-between">
              <div>
                <Text type="secondary" className="text-sm">
                  {stat.title}
                </Text>
                <Statistic
                  value={stat.value}
                  prefix={stat.prefix}
                  valueStyle={{ fontSize: '28px', fontWeight: 600 }}
                />
                {stat.change !== undefined && (
                  <Text type="secondary" className="text-xs">
                    {stat.changeLabel}: {stat.prefix || ''}{stat.change.toLocaleString()}
                  </Text>
                )}
                {stat.percentage !== undefined && (
                  <Text type="secondary" className="text-xs">
                    占比: {stat.percentage}%
                  </Text>
                )}
              </div>
              {stat.icon}
            </div>
          </Card>
        </Col>
      ))}
    </Row>
  );
}

interface PlanDistributionProps {
  distribution: Array<{ plan: string; count: number; percentage: number }>;
  loading?: boolean;
}

const planColors: Record<string, string> = {
  free: '#8c8c8c',
  basic: '#1890ff',
  professional: '#52c41a',
  enterprise: '#722ed1',
};

const planLabels: Record<string, string> = {
  free: '免费版',
  basic: '基础版',
  professional: '专业版',
  enterprise: '企业版',
};

export function PlanDistribution({ distribution, loading }: PlanDistributionProps) {
  return (
    <Card title="套餐分布" loading={loading}>
      <div className="space-y-4">
        {distribution.map((item) => (
          <div key={item.plan}>
            <div className="flex justify-between mb-1">
              <Text>{planLabels[item.plan] || item.plan}</Text>
              <Text type="secondary">
                {item.count} ({item.percentage.toFixed(1)}%)
              </Text>
            </div>
            <Progress
              percent={item.percentage}
              showInfo={false}
              strokeColor={planColors[item.plan] || '#1890ff'}
            />
          </div>
        ))}
      </div>
    </Card>
  );
}

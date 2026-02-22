'use client';

import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Select, Spin, message, Typography } from 'antd';
import { ThunderboltOutlined, CloudOutlined, ApiOutlined } from '@ant-design/icons';
import { UsageChart, TopTenantsUsage } from '@/components/admin/statistics';
import { adminStatisticsApi } from '@/lib/api/admin';
import { UsageStatistics } from '@/types/admin';

const { Title } = Typography;

const periodOptions = [
  { value: 'day', label: '按日' },
  { value: 'week', label: '按周' },
  { value: 'month', label: '按月' },
  { value: 'year', label: '按年' },
];

export default function UsagePage() {
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<'day' | 'week' | 'month' | 'year'>('month');
  const [statistics, setStatistics] = useState<UsageStatistics | null>(null);

  useEffect(() => {
    fetchUsage();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period]);

  const fetchUsage = async () => {
    setLoading(true);
    try {
      const response = await adminStatisticsApi.getUsage(period);
      if (response.success && response.data) {
        setStatistics(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch usage:', error);
      message.error('加载用量统计失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !statistics) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <Title level={4}>用量分析</Title>
        <Select
          value={period}
          onChange={(value) => setPeriod(value)}
          options={periodOptions}
          style={{ width: 120 }}
        />
      </div>

      {/* Usage summary */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Token 总消耗"
              value={statistics?.total_tokens || 0}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="存储使用量"
              value={statistics?.storage_usage || 0}
              prefix={<CloudOutlined />}
              suffix="MB"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="API 调用次数"
              value={statistics?.api_calls || 0}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Usage trend */}
        <Col xs={24} lg={12}>
          <UsageChart
            data={statistics?.usage_trend || []}
            title="Token 消耗趋势"
            loading={loading}
          />
        </Col>

        {/* Top tenants */}
        <Col xs={24} lg={12}>
          <TopTenantsUsage
            tenants={statistics?.tokens_by_tenant || []}
            title="Top 租户 Token 消耗"
            loading={loading}
          />
        </Col>
      </Row>
    </div>
  );
}

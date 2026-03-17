'use client';

import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Select, message, Typography, Table } from 'antd';
import Skeleton from '@/components/ui/Loading/Skeleton';
import type { ColumnsType } from 'antd/es/table';
import { DollarOutlined } from '@ant-design/icons';
import { RevenueChart } from '@/components/admin/statistics';
import { adminStatisticsApi } from '@/lib/api/admin';
import { RevenueStatistics } from '@/types/admin';

const { Title, Text } = Typography;

const periodOptions = [
  { value: 'day', label: '按日' },
  { value: 'week', label: '按周' },
  { value: 'month', label: '按月' },
  { value: 'year', label: '按年' },
];

export default function RevenuePage() {
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<'day' | 'week' | 'month' | 'year'>('month');
  const [statistics, setStatistics] = useState<RevenueStatistics | null>(null);

  useEffect(() => {
    fetchRevenue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period]);

  const fetchRevenue = async () => {
    setLoading(true);
    try {
      const response = await adminStatisticsApi.getRevenue(period);
      if (response.success && response.data) {
        setStatistics(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch revenue:', error);
      message.error('加载收入统计失败');
    } finally {
      setLoading(false);
    }
  };

  const revenueByPlanColumns: ColumnsType<{ plan: string; revenue: number }> = [
    {
      title: '套餐',
      dataIndex: 'plan',
      key: 'plan',
      render: (plan: string) => {
        const labels: Record<string, string> = {
          free: '免费版',
          trial: '试用版',
          monthly: '月付版',
          quarterly: '季付版',
          semi_annual: '半年付',
          annual: '年付版',
        };
        return labels[plan] || plan;
      },
    },
    {
      title: '收入',
      dataIndex: 'revenue',
      key: 'revenue',
      render: (revenue: number) => (
        <Text strong>¥{revenue.toLocaleString()}</Text>
      ),
    },
    {
      title: '占比',
      key: 'percentage',
      render: (_, record) => {
        const total = statistics?.total_revenue || 1;
        const percentage = ((record.revenue / total) * 100).toFixed(1);
        return `${percentage}%`;
      },
    },
  ];

  if (loading && !statistics) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <Skeleton variant="text" width="15%" height={28} />
          <Skeleton variant="rectangular" width={120} height={32} />
        </div>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={8}>
            <div className="bg-white rounded-xl p-5 border border-neutral-200">
              <Skeleton variant="text" width="40%" />
              <Skeleton variant="rectangular" height={36} className="mt-3" />
            </div>
          </Col>
          <Col xs={24} sm={16}>
            <div className="bg-white rounded-xl p-5 border border-neutral-200">
              <Skeleton variant="text" width="30%" className="mb-3" />
              <Skeleton variant="rectangular" height={150} />
            </div>
          </Col>
        </Row>
        <Row gutter={[16, 16]}>
          {[0, 1].map((i) => (
            <Col xs={24} lg={12} key={i}>
              <div className="bg-white rounded-xl p-5 border border-neutral-200">
                <Skeleton variant="text" width="35%" className="mb-3" />
                <Skeleton variant="table" rows={4} />
              </div>
            </Col>
          ))}
        </Row>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <Title level={4}>收入统计</Title>
        <Select
          value={period}
          onChange={(value) => setPeriod(value)}
          options={periodOptions}
          style={{ width: 120 }}
        />
      </div>

      {/* Revenue summary */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="总收入"
              value={statistics?.total_revenue || 0}
              prefix={<DollarOutlined />}
              suffix="元"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={16}>
          <Card title="收入趋势" loading={loading}>
            <RevenueChart
              data={statistics?.revenue_trend || []}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Revenue by plan */}
        <Col xs={24} lg={12}>
          <Card title="按套餐收入" loading={loading}>
            <Table
              dataSource={statistics?.revenue_by_plan || []}
              columns={revenueByPlanColumns}
              rowKey="plan"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>

        {/* Daily revenue */}
        <Col xs={24} lg={12}>
          <Card title="每日收入" loading={loading}>
            <div className="max-h-64 overflow-y-auto">
              {(statistics?.daily_revenue || []).slice(-14).reverse().map((item) => (
                <div
                  key={item.date}
                  className="flex justify-between py-2 border-b border-gray-100"
                >
                  <Text>{item.date}</Text>
                  <Text strong>¥{item.value.toLocaleString()}</Text>
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

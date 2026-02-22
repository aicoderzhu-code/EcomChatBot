'use client';

import { useEffect, useState } from 'react';
import { Row, Col, Card, Spin, message, Typography } from 'antd';
import { PlatformOverview, PlanDistribution } from '@/components/admin/statistics';
import { adminStatisticsApi } from '@/lib/api/admin';
import { PlatformStatistics } from '@/types/admin';

const { Title } = Typography;

export default function StatisticsPage() {
  const [loading, setLoading] = useState(true);
  const [statistics, setStatistics] = useState<PlatformStatistics | null>(null);

  useEffect(() => {
    fetchStatistics();
  }, []);

  const fetchStatistics = async () => {
    setLoading(true);
    try {
      const response = await adminStatisticsApi.getOverview();
      if (response.success && response.data) {
        setStatistics(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
      message.error('加载统计数据失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Title level={4}>统计概览</Title>

      {/* Overview cards */}
      <PlatformOverview statistics={statistics} loading={loading} />

      <Row gutter={[16, 16]}>
        {/* Plan distribution */}
        <Col xs={24} lg={8}>
          <PlanDistribution
            distribution={
              statistics?.plan_distribution
                ? Object.entries(statistics.plan_distribution).map(([plan, count]) => {
                    const total = Object.values(statistics.plan_distribution).reduce((a, b) => a + b, 0);
                    return {
                      plan,
                      count,
                      percentage: total > 0 ? (count / total) * 100 : 0,
                    };
                  })
                : []
            }
            loading={loading}
          />
        </Col>

        {/* Revenue summary */}
        <Col xs={24} lg={16}>
          <Card title="收入概览" loading={loading}>
            <Row gutter={16}>
              <Col span={8}>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    ¥{(statistics?.revenue_stats?.this_month || 0).toLocaleString()}
                  </div>
                  <div className="text-gray-500 text-sm">本月收入</div>
                </div>
              </Col>
              <Col span={8}>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    ¥{(statistics?.revenue_stats?.mrr || 0).toLocaleString()}
                  </div>
                  <div className="text-gray-500 text-sm">MRR</div>
                </div>
              </Col>
              <Col span={8}>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    ¥{(statistics?.revenue_stats?.arr || 0).toLocaleString()}
                  </div>
                  <div className="text-gray-500 text-sm">ARR</div>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Tenant stats */}
        <Col xs={24}>
          <Card title="租户统计" loading={loading}>
            <Row gutter={16}>
              <Col span={4}>
                <div className="text-center">
                  <div className="text-xl font-bold">{statistics?.tenant_stats?.total || 0}</div>
                  <div className="text-gray-500 text-sm">总租户</div>
                </div>
              </Col>
              <Col span={4}>
                <div className="text-center">
                  <div className="text-xl font-bold text-green-600">{statistics?.tenant_stats?.active || 0}</div>
                  <div className="text-gray-500 text-sm">活跃租户</div>
                </div>
              </Col>
              <Col span={4}>
                <div className="text-center">
                  <div className="text-xl font-bold text-blue-600">{statistics?.tenant_stats?.paid || 0}</div>
                  <div className="text-gray-500 text-sm">付费租户</div>
                </div>
              </Col>
              <Col span={4}>
                <div className="text-center">
                  <div className="text-xl font-bold text-orange-600">{statistics?.tenant_stats?.trial || 0}</div>
                  <div className="text-gray-500 text-sm">试用租户</div>
                </div>
              </Col>
              <Col span={4}>
                <div className="text-center">
                  <div className="text-xl font-bold text-purple-600">{statistics?.tenant_stats?.new_this_month || 0}</div>
                  <div className="text-gray-500 text-sm">本月新增</div>
                </div>
              </Col>
              <Col span={4}>
                <div className="text-center">
                  <div className="text-xl font-bold text-red-600">{statistics?.tenant_stats?.churn_rate?.toFixed(1) || 0}%</div>
                  <div className="text-gray-500 text-sm">流失率</div>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

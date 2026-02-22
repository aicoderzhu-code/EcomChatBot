'use client';

import { useEffect, useState } from 'react';
import { Card, Row, Col, Table, Typography, Space, Tag, Spin, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { TeamOutlined, AlertOutlined } from '@ant-design/icons';
import PlatformOverview, { PlanDistribution } from '@/components/admin/statistics/PlatformOverview';
import { adminStatisticsApi, adminTenantsApi } from '@/lib/api/admin';
import { PlatformStatistics, TenantInfo, OverdueTenantInfo } from '@/types/admin';

const { Title, Text } = Typography;

export default function PlatformPage() {
  const [loading, setLoading] = useState(true);
  const [statistics, setStatistics] = useState<PlatformStatistics | null>(null);
  const [recentTenants, setRecentTenants] = useState<TenantInfo[]>([]);
  const [overdueTenants, setOverdueTenants] = useState<OverdueTenantInfo[]>([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch statistics and recent data in parallel
      const [statsRes, tenantsRes, overdueRes] = await Promise.all([
        adminStatisticsApi.getOverview(),
        adminTenantsApi.list({ page: 1, size: 5 }),
        adminTenantsApi.getOverdue(1, 5),
      ]);

      if (statsRes.success && statsRes.data) {
        setStatistics(statsRes.data);
      }

      if (tenantsRes.success && tenantsRes.data) {
        setRecentTenants(tenantsRes.data.items);
      }

      if (overdueRes.success && overdueRes.data) {
        setOverdueTenants(overdueRes.data.items);
      }
    } catch (error) {
      console.error('Failed to fetch platform data:', error);
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const tenantColumns: ColumnsType<TenantInfo> = [
    {
      title: '公司名称',
      dataIndex: 'company_name',
      key: 'company_name',
      ellipsis: true,
    },
    {
      title: '联系邮箱',
      dataIndex: 'contact_email',
      key: 'contact_email',
      ellipsis: true,
    },
    {
      title: '套餐',
      dataIndex: 'current_plan',
      key: 'current_plan',
      render: (plan: string) => {
        const planColors: Record<string, string> = {
          free: 'default',
          basic: 'blue',
          professional: 'green',
          enterprise: 'purple',
        };
        const planLabels: Record<string, string> = {
          free: '免费版',
          basic: '基础版',
          professional: '专业版',
          enterprise: '企业版',
        };
        return <Tag color={planColors[plan] || 'default'}>{planLabels[plan] || plan}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusColors: Record<string, string> = {
          active: 'green',
          suspended: 'red',
          pending: 'orange',
        };
        const statusLabels: Record<string, string> = {
          active: '正常',
          suspended: '已停用',
          pending: '待激活',
        };
        return <Tag color={statusColors[status] || 'default'}>{statusLabels[status] || status}</Tag>;
      },
    },
  ];

  const overdueColumns: ColumnsType<OverdueTenantInfo> = [
    {
      title: '公司名称',
      dataIndex: 'company_name',
      key: 'company_name',
      ellipsis: true,
    },
    {
      title: '欠费金额',
      dataIndex: 'total_overdue',
      key: 'total_overdue',
      render: (amount: number) => (
        <Text type="danger">¥{amount.toFixed(2)}</Text>
      ),
    },
    {
      title: '逾期天数',
      dataIndex: 'days_overdue',
      key: 'days_overdue',
      render: (days: number) => (
        <Tag color={days > 30 ? 'red' : days > 7 ? 'orange' : 'gold'}>
          {days} 天
        </Tag>
      ),
    },
    {
      title: '欠费账单数',
      dataIndex: 'overdue_bills_count',
      key: 'overdue_bills_count',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Title level={4}>平台概览</Title>

      {/* Statistics Cards */}
      <PlatformOverview statistics={statistics} loading={loading} />

      <Row gutter={[16, 16]}>
        {/* Plan Distribution */}
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

        {/* Recent Tenants */}
        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <TeamOutlined />
                <span>最近注册租户</span>
              </Space>
            }
            extra={<a href="/tenants">查看全部</a>}
          >
            <Table
              dataSource={recentTenants}
              columns={tenantColumns}
              rowKey="tenant_id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* Overdue Tenants */}
      <Card
        title={
          <Space>
            <AlertOutlined className="text-red-500" />
            <span>欠费租户预警</span>
          </Space>
        }
        extra={<a href="/tenants/overdue">查看全部</a>}
      >
        {overdueTenants.length > 0 ? (
          <Table
            dataSource={overdueTenants}
            columns={overdueColumns}
            rowKey="tenant_id"
            pagination={false}
            size="small"
          />
        ) : (
          <div className="text-center py-8">
            <Text type="secondary">暂无欠费租户</Text>
          </div>
        )}
      </Card>
    </div>
  );
}

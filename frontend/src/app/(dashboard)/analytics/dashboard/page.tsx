'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Row, Col, Statistic, Select, Space, Table, Typography, Tag, message, Spin,
} from 'antd';
import {
  BarChartOutlined, DollarOutlined, ShoppingOutlined,
  RiseOutlined, FallOutlined, UserOutlined,
} from '@ant-design/icons';
import { analyticsApi } from '@/lib/api/analytics';
import type { OrderOverview, TopProduct, BuyerStat } from '@/lib/api/analytics';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;

export default function SalesDashboardPage() {
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [overview, setOverview] = useState<OrderOverview | null>(null);
  const [topProducts, setTopProducts] = useState<TopProduct[]>([]);
  const [buyerStats, setBuyerStats] = useState<BuyerStat[]>([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [overviewResp, productsResp, buyersResp] = await Promise.all([
        analyticsApi.getOrderOverview(days),
        analyticsApi.getTopProducts(days, 10),
        analyticsApi.getBuyerStats(days, 10),
      ]);
      if (overviewResp.success && overviewResp.data) {
        setOverview(overviewResp.data);
      }
      if (productsResp.success && productsResp.data) {
        setTopProducts(productsResp.data);
      }
      if (buyersResp.success && buyersResp.data) {
        setBuyerStats(buyersResp.data);
      }
    } catch {
      message.error('加载分析数据失败');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const productColumns: ColumnsType<TopProduct> = [
    {
      title: '排名',
      width: 60,
      render: (_: unknown, __: TopProduct, index: number) => (
        <Tag color={index < 3 ? 'gold' : 'default'}>{index + 1}</Tag>
      ),
    },
    {
      title: '商品名称',
      dataIndex: 'product_title',
      ellipsis: true,
    },
    {
      title: '订单数',
      dataIndex: 'order_count',
      width: 80,
      align: 'center',
    },
    {
      title: '销售额',
      dataIndex: 'total_revenue',
      width: 120,
      render: (v: number) => (
        <Text strong style={{ color: '#cf1322' }}>&yen;{v.toFixed(2)}</Text>
      ),
    },
    {
      title: '销量',
      dataIndex: 'total_quantity',
      width: 80,
      align: 'center',
    },
  ];

  const buyerColumns: ColumnsType<BuyerStat> = [
    {
      title: '排名',
      width: 60,
      render: (_: unknown, __: BuyerStat, index: number) => (
        <Tag color={index < 3 ? 'gold' : 'default'}>{index + 1}</Tag>
      ),
    },
    {
      title: '买家ID',
      dataIndex: 'buyer_id',
      ellipsis: true,
    },
    {
      title: '订单数',
      dataIndex: 'order_count',
      width: 80,
      align: 'center',
    },
    {
      title: '消费总额',
      dataIndex: 'total_spent',
      width: 120,
      render: (v: number) => (
        <Text strong>&yen;{v.toFixed(2)}</Text>
      ),
    },
  ];

  // 简单文本柱状图
  const renderBarChart = (data: Array<{ date: string; orders: number; revenue: number }>) => {
    if (!data || data.length === 0) return <Text type="secondary">暂无数据</Text>;
    const maxRevenue = Math.max(...data.map(d => d.revenue), 1);
    return (
      <div style={{ overflowX: 'auto' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: 120, minWidth: data.length * 30 }}>
          {data.map((d, i) => {
            const height = Math.max((d.revenue / maxRevenue) * 100, 2);
            return (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, minWidth: 24 }}>
                <Text style={{ fontSize: 10 }}>{d.orders}</Text>
                <div
                  style={{
                    width: '100%',
                    maxWidth: 28,
                    height,
                    background: 'linear-gradient(180deg, #1677ff 0%, #69b1ff 100%)',
                    borderRadius: '4px 4px 0 0',
                    cursor: 'pointer',
                  }}
                  title={`${d.date}\n订单: ${d.orders}\n营收: ¥${d.revenue.toFixed(2)}`}
                />
                <Text style={{ fontSize: 9, transform: 'rotate(-45deg)', whiteSpace: 'nowrap', marginTop: 4 }}>
                  {d.date.slice(5)}
                </Text>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // 状态分布
  const renderStatusDist = (dist: Record<string, number>) => {
    const statusLabels: Record<string, { label: string; color: string }> = {
      pending: { label: '待付款', color: '#d9d9d9' },
      paid: { label: '已付款', color: '#1677ff' },
      shipped: { label: '已发货', color: '#13c2c2' },
      completed: { label: '已完成', color: '#52c41a' },
      refunded: { label: '已退款', color: '#fa8c16' },
      cancelled: { label: '已取消', color: '#f5222d' },
    };
    const total = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
    return (
      <div>
        {Object.entries(dist).map(([key, value]) => {
          const info = statusLabels[key] || { label: key, color: '#d9d9d9' };
          const pct = ((value / total) * 100).toFixed(1);
          return (
            <div key={key} style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                <Text style={{ fontSize: 12 }}>{info.label}</Text>
                <Text style={{ fontSize: 12 }}>{value} ({pct}%)</Text>
              </div>
              <div style={{ height: 8, background: '#f0f0f0', borderRadius: 4 }}>
                <div
                  style={{
                    height: '100%',
                    width: `${pct}%`,
                    background: info.color,
                    borderRadius: 4,
                    transition: 'width 0.3s',
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>
            <BarChartOutlined style={{ marginRight: 8 }} />
            销售看板
          </Title>
        </Col>
        <Col>
          <Space>
            <Text>统计周期：</Text>
            <Select
              value={days}
              onChange={setDays}
              style={{ width: 120 }}
              options={[
                { value: 7, label: '近7天' },
                { value: 14, label: '近14天' },
                { value: 30, label: '近30天' },
                { value: 60, label: '近60天' },
                { value: 90, label: '近90天' },
              ]}
            />
          </Space>
        </Col>
      </Row>

      <Spin spinning={loading}>
        {/* 核心指标 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总订单数"
                value={overview?.total_orders || 0}
                prefix={<ShoppingOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="总营收"
                value={overview?.total_revenue || 0}
                prefix={<DollarOutlined />}
                precision={2}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均客单价"
                value={overview?.avg_order_value || 0}
                prefix={<RiseOutlined />}
                precision={2}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="退款金额"
                value={overview?.refund_total || 0}
                prefix={<FallOutlined />}
                precision={2}
                valueStyle={{ color: '#fa8c16' }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                退款 {overview?.refund_count || 0} 笔
              </Text>
            </Card>
          </Col>
        </Row>

        {/* 趋势图和状态分布 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={16}>
            <Card title="每日订单趋势" size="small">
              {overview?.daily_trend
                ? renderBarChart(overview.daily_trend)
                : <Text type="secondary">暂无数据</Text>
              }
            </Card>
          </Col>
          <Col span={8}>
            <Card title="订单状态分布" size="small">
              {overview?.status_distribution
                ? renderStatusDist(overview.status_distribution)
                : <Text type="secondary">暂无数据</Text>
              }
            </Card>
          </Col>
        </Row>

        {/* 排行榜 */}
        <Row gutter={16}>
          <Col span={14}>
            <Card
              title={
                <Space>
                  <ShoppingOutlined />
                  <span>热销商品 TOP10</span>
                </Space>
              }
              size="small"
            >
              <Table
                columns={productColumns}
                dataSource={topProducts}
                rowKey="product_title"
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
          <Col span={10}>
            <Card
              title={
                <Space>
                  <UserOutlined />
                  <span>高价值买家 TOP10</span>
                </Space>
              }
              size="small"
            >
              <Table
                columns={buyerColumns}
                dataSource={buyerStats}
                rowKey="buyer_id"
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
}

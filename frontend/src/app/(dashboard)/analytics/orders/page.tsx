'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Input, Select, Space, Tag,
  message, Modal, Typography, Descriptions, Row, Col, Statistic,
} from 'antd';
import {
  SyncOutlined, ShoppingOutlined,
  DollarOutlined, OrderedListOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { analyticsApi } from '@/lib/api/analytics';
import type { OrderItem } from '@/lib/api/analytics';

const { Search } = Input;
const { Text, Title } = Typography;

const statusTagMap: Record<string, { color: string; text: string }> = {
  pending: { color: 'default', text: '待付款' },
  paid: { color: 'blue', text: '已付款' },
  shipped: { color: 'cyan', text: '已发货' },
  completed: { color: 'green', text: '已完成' },
  refunded: { color: 'orange', text: '已退款' },
  cancelled: { color: 'red', text: '已取消' },
};

export default function OrdersPage() {
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

  // 详情弹窗
  const [selectedOrder, setSelectedOrder] = useState<OrderItem | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // 统计
  const [stats, setStats] = useState<{
    total_orders: number;
    total_revenue: number;
    avg_order_value: number;
  } | null>(null);

  const loadOrders = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await analyticsApi.listOrders({
        keyword: keyword || undefined,
        status: statusFilter,
        page,
        size,
      });
      if (resp.success && resp.data) {
        setOrders(resp.data.items);
        setTotal(resp.data.total);
      }
    } catch {
      message.error('加载订单列表失败');
    } finally {
      setLoading(false);
    }
  }, [keyword, statusFilter, page, size]);

  const loadStats = useCallback(async () => {
    try {
      const resp = await analyticsApi.getOrderOverview(30);
      if (resp.success && resp.data) {
        setStats({
          total_orders: resp.data.total_orders,
          total_revenue: resp.data.total_revenue,
          avg_order_value: resp.data.avg_order_value,
        });
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const resp = await analyticsApi.triggerOrderSync(1);
      if (resp.success) {
        message.success('订单同步任务已创建');
        setTimeout(() => loadOrders(), 2000);
      } else {
        message.error((resp.error as { message?: string })?.message || '触发同步失败');
      }
    } catch {
      message.error('触发同步失败');
    } finally {
      setSyncing(false);
    }
  };

  const columns: ColumnsType<OrderItem> = [
    {
      title: '订单号',
      dataIndex: 'platform_order_id',
      width: 180,
      render: (id: string, record) => (
        <a onClick={() => { setSelectedOrder(record); setDetailOpen(true); }}>{id}</a>
      ),
    },
    {
      title: '商品标题',
      dataIndex: 'product_title',
      ellipsis: true,
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      width: 70,
      align: 'center',
    },
    {
      title: '单价',
      dataIndex: 'unit_price',
      width: 100,
      render: (price: number) => (
        <Text>&yen;{Number(price).toFixed(2)}</Text>
      ),
    },
    {
      title: '总金额',
      dataIndex: 'total_amount',
      width: 110,
      render: (amount: number) => (
        <Text strong style={{ color: '#f5222d' }}>&yen;{Number(amount).toFixed(2)}</Text>
      ),
    },
    {
      title: '买家ID',
      dataIndex: 'buyer_id',
      width: 120,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (status: string) => {
        const tag = statusTagMap[status] || { color: 'default', text: status };
        return <Tag color={tag.color}>{tag.text}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        <OrderedListOutlined style={{ marginRight: 8 }} />
        订单分析
      </Title>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="订单总数(30天)"
              value={stats?.total_orders || 0}
              prefix={<ShoppingOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总营收(30天)"
              value={stats?.total_revenue || 0}
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
              value={stats?.avg_order_value || 0}
              precision={2}
              prefix="&yen;"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Button
              type="primary"
              icon={<SyncOutlined spin={syncing} />}
              loading={syncing}
              onClick={handleSync}
              block
              size="large"
            >
              同步订单
            </Button>
          </Card>
        </Col>
      </Row>

      {/* 搜索和筛选 */}
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Search
            placeholder="搜索订单号/商品标题"
            allowClear
            style={{ width: 300 }}
            onSearch={(value) => { setKeyword(value); setPage(1); }}
          />
          <Select
            placeholder="订单状态"
            allowClear
            style={{ width: 120 }}
            value={statusFilter}
            onChange={(value) => { setStatusFilter(value); setPage(1); }}
            options={[
              { value: 'pending', label: '待付款' },
              { value: 'paid', label: '已付款' },
              { value: 'shipped', label: '已发货' },
              { value: 'completed', label: '已完成' },
              { value: 'refunded', label: '已退款' },
              { value: 'cancelled', label: '已取消' },
            ]}
          />
        </Space>
      </Card>

      {/* 订单表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={orders}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: size,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 笔订单`,
            onChange: (p, s) => { setPage(p); setSize(s); },
          }}
        />
      </Card>

      {/* 订单详情弹窗 */}
      <Modal
        title="订单详情"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={650}
      >
        {selectedOrder && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="平台订单号" span={2}>
              {selectedOrder.platform_order_id}
            </Descriptions.Item>
            <Descriptions.Item label="商品标题" span={2}>
              {selectedOrder.product_title}
            </Descriptions.Item>
            <Descriptions.Item label="数量">{selectedOrder.quantity}</Descriptions.Item>
            <Descriptions.Item label="单价">&yen;{Number(selectedOrder.unit_price).toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="总金额">
              <Text strong style={{ color: '#f5222d' }}>
                &yen;{Number(selectedOrder.total_amount).toFixed(2)}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={statusTagMap[selectedOrder.status]?.color}>
                {statusTagMap[selectedOrder.status]?.text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="买家ID">{selectedOrder.buyer_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="退款金额">
              {selectedOrder.refund_amount != null
                ? `¥${Number(selectedOrder.refund_amount).toFixed(2)}`
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="支付时间">
              {selectedOrder.paid_at ? new Date(selectedOrder.paid_at).toLocaleString('zh-CN') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="发货时间">
              {selectedOrder.shipped_at ? new Date(selectedOrder.shipped_at).toLocaleString('zh-CN') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="完成时间">
              {selectedOrder.completed_at ? new Date(selectedOrder.completed_at).toLocaleString('zh-CN') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {new Date(selectedOrder.created_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}

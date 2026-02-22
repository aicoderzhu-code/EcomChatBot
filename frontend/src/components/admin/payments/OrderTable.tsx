'use client';

import { Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import Link from 'next/link';
import { PaymentOrderInfo, PaymentOrderStatus } from '@/types/admin';

const { Text } = Typography;

interface OrderTableProps {
  orders: PaymentOrderInfo[];
  loading?: boolean;
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number, pageSize: number) => void;
}

const statusConfig: Record<PaymentOrderStatus, { color: string; label: string }> = {
  pending: { color: 'orange', label: '待支付' },
  paid: { color: 'green', label: '已支付' },
  failed: { color: 'red', label: '支付失败' },
  refunded: { color: 'default', label: '已退款' },
  cancelled: { color: 'default', label: '已取消' },
};

const paymentMethodLabels: Record<string, string> = {
  alipay: '支付宝',
  wechat: '微信支付',
  bank_transfer: '银行转账',
  credit_card: '信用卡',
};

export default function OrderTable({
  orders,
  loading,
  total,
  page,
  pageSize,
  onPageChange,
}: OrderTableProps) {
  const columns: ColumnsType<PaymentOrderInfo> = [
    {
      title: '订单号',
      dataIndex: 'order_id',
      key: 'order_id',
      width: 180,
      ellipsis: true,
    },
    {
      title: '租户',
      key: 'tenant',
      width: 150,
      render: (_, record) => (
        <Link href={`/tenants/${record.tenant_id}`} className="text-blue-600">
          {record.company_name || record.tenant_id.slice(0, 8) + '...'}
        </Link>
      ),
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      render: (amount: number) => (
        <Text strong>¥{amount.toFixed(2)}</Text>
      ),
    },
    {
      title: '支付方式',
      dataIndex: 'payment_method',
      key: 'payment_method',
      width: 100,
      render: (method: string) => paymentMethodLabels[method] || method,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: PaymentOrderStatus) => {
        const config = statusConfig[status] || { color: 'default', label: status };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '支付时间',
      dataIndex: 'paid_at',
      key: 'paid_at',
      width: 180,
      render: (date: string | null) => date ? new Date(date).toLocaleString('zh-CN') : '-',
    },
  ];

  return (
    <Table
      dataSource={orders}
      columns={columns}
      rowKey="order_id"
      loading={loading}
      pagination={{
        current: page,
        pageSize,
        total,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total) => `共 ${total} 条`,
        onChange: onPageChange,
      }}
      scroll={{ x: 1100 }}
    />
  );
}

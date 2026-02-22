'use client';

import { Table, Tag, Button, Space, Typography, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { PendingBillInfo, BillInfo, BillStatus } from '@/types/admin';

const { Text } = Typography;

interface BillTableProps {
  bills: PendingBillInfo[] | BillInfo[];
  loading?: boolean;
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number, pageSize: number) => void;
  onApprove?: (billId: string) => void;
  onReject?: (billId: string) => void;
  showActions?: boolean;
}

const statusConfig: Record<BillStatus, { color: string; label: string }> = {
  pending: { color: 'orange', label: '待审核' },
  approved: { color: 'blue', label: '已审核' },
  paid: { color: 'green', label: '已支付' },
  overdue: { color: 'red', label: '已逾期' },
  rejected: { color: 'default', label: '已拒绝' },
  refunded: { color: 'default', label: '已退款' },
};

export default function BillTable({
  bills,
  loading,
  total,
  page,
  pageSize,
  onPageChange,
  onApprove,
  onReject,
  showActions = false,
}: BillTableProps) {
  const columns: ColumnsType<PendingBillInfo | BillInfo> = [
    {
      title: '账单号',
      dataIndex: 'bill_id',
      key: 'bill_id',
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
      title: '账期',
      key: 'period',
      width: 200,
      render: (_, record) => (
        <span>
          {new Date(record.billing_period_start).toLocaleDateString('zh-CN')} ~{' '}
          {new Date(record.billing_period_end).toLocaleDateString('zh-CN')}
        </span>
      ),
    },
    {
      title: '到期日期',
      dataIndex: 'due_date',
      key: 'due_date',
      width: 120,
      render: (date: string) => new Date(date).toLocaleDateString('zh-CN'),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
  ];

  // Add status column for BillInfo (not PendingBillInfo)
  if ((bills[0] as BillInfo)?.status !== undefined) {
    columns.splice(4, 0, {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: BillStatus) => {
        const config = statusConfig[status] || { color: 'default', label: status };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    });
  }

  // Add actions column if needed
  if (showActions && onApprove && onReject) {
    columns.push({
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="审核通过">
            <Button
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => onApprove(record.bill_id)}
            >
              通过
            </Button>
          </Tooltip>
          <Tooltip title="拒绝">
            <Button
              type="link"
              size="small"
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => onReject(record.bill_id)}
            >
              拒绝
            </Button>
          </Tooltip>
        </Space>
      ),
    });
  }

  return (
    <Table
      dataSource={bills}
      columns={columns}
      rowKey="bill_id"
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
      scroll={{ x: 1200 }}
    />
  );
}

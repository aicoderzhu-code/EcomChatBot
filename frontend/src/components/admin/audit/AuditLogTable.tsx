'use client';

import { Table, Tag, Typography, Tooltip, Button } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { EyeOutlined } from '@ant-design/icons';
import { AuditLog } from '@/types/admin';

const { Text } = Typography;

interface AuditLogTableProps {
  logs: AuditLog[];
  loading?: boolean;
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number, pageSize: number) => void;
  onViewDetails?: (log: AuditLog) => void;
}

const operationTypeLabels: Record<string, { label: string; color: string }> = {
  tenant_create: { label: '创建租户', color: 'green' },
  tenant_update: { label: '更新租户', color: 'blue' },
  tenant_delete: { label: '删除租户', color: 'red' },
  tenant_suspend: { label: '停用租户', color: 'orange' },
  tenant_activate: { label: '启用租户', color: 'green' },
  plan_change: { label: '套餐变更', color: 'purple' },
  quota_adjustment: { label: '配额调整', color: 'cyan' },
  reset_api_key: { label: '重置API Key', color: 'gold' },
  approve_bill: { label: '审核账单', color: 'blue' },
  reject_bill: { label: '拒绝账单', color: 'red' },
  send_payment_reminder: { label: '发送催款', color: 'orange' },
  admin_create: { label: '创建管理员', color: 'green' },
  admin_update: { label: '更新管理员', color: 'blue' },
  admin_delete: { label: '删除管理员', color: 'red' },
  batch_operation: { label: '批量操作', color: 'purple' },
  login: { label: '登录', color: 'default' },
  logout: { label: '登出', color: 'default' },
};

const resourceTypeLabels: Record<string, string> = {
  tenant: '租户',
  subscription: '订阅',
  admin: '管理员',
  bill: '账单',
  payment: '支付',
  system: '系统',
};

export default function AuditLogTable({
  logs,
  loading,
  total,
  page,
  pageSize,
  onPageChange,
  onViewDetails,
}: AuditLogTableProps) {
  const columns: ColumnsType<AuditLog> = [
    {
      title: '操作时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作人',
      key: 'admin',
      width: 120,
      render: (_, record) => record.admin_username || record.admin_id.slice(0, 8) + '...',
    },
    {
      title: '操作类型',
      dataIndex: 'operation_type',
      key: 'operation_type',
      width: 120,
      render: (type: string) => {
        const config = operationTypeLabels[type] || { label: type, color: 'default' };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      key: 'resource_type',
      width: 100,
      render: (type: string) => resourceTypeLabels[type] || type,
    },
    {
      title: '资源 ID',
      dataIndex: 'resource_id',
      key: 'resource_id',
      width: 150,
      ellipsis: true,
      render: (id: string) => (
        <Tooltip title={id}>
          <Text copyable={{ text: id }}>{id.slice(0, 12)}...</Text>
        </Tooltip>
      ),
    },
    {
      title: 'IP 地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
      render: (ip: string | null) => ip || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      fixed: 'right',
      render: (_, record) => (
        <Tooltip title="查看详情">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => onViewDetails?.(record)}
          />
        </Tooltip>
      ),
    },
  ];

  return (
    <Table
      dataSource={logs}
      columns={columns}
      rowKey="log_id"
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
      scroll={{ x: 1000 }}
    />
  );
}

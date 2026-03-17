'use client';

import { Table, Tag, Button, Space, Tooltip, Dropdown } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { MenuProps } from 'antd';
import {
  EyeOutlined,
  MoreOutlined,
  StopOutlined,
  CheckCircleOutlined,
  KeyOutlined,
} from '@ant-design/icons';
import Link from 'next/link';
import { TenantInfo, TenantStatus } from '@/types/admin';

interface TenantTableProps {
  tenants: TenantInfo[];
  loading?: boolean;
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number, pageSize: number) => void;
  onStatusChange: (tenantId: string, status: TenantStatus) => void;
  onResetApiKey: (tenantId: string) => void;
  selectedRowKeys?: string[];
  onSelectChange?: (selectedRowKeys: string[]) => void;
}

const statusConfig: Record<string, { color: string; label: string }> = {
  active: { color: 'green', label: '正常' },
  suspended: { color: 'red', label: '已停用' },
  pending: { color: 'orange', label: '待激活' },
  deleted: { color: 'default', label: '已删除' },
};

const planConfig: Record<string, { color: string; label: string }> = {
  free: { color: 'default', label: '免费版' },
  trial: { color: 'cyan', label: '试用版' },
  monthly: { color: 'blue', label: '月付版' },
  quarterly: { color: 'geekblue', label: '季付版' },
  semi_annual: { color: 'purple', label: '半年付' },
  annual: { color: 'gold', label: '年付版' },
};

export default function TenantTable({
  tenants,
  loading,
  total,
  page,
  pageSize,
  onPageChange,
  onStatusChange,
  onResetApiKey,
  selectedRowKeys,
  onSelectChange,
}: TenantTableProps) {
  const getActionMenu = (record: TenantInfo): MenuProps['items'] => [
    {
      key: 'status',
      label: record.status === 'active' ? '停用租户' : '启用租户',
      icon: record.status === 'active' ? <StopOutlined /> : <CheckCircleOutlined />,
      onClick: () => onStatusChange(record.tenant_id, record.status === 'active' ? 'suspended' : 'active'),
    },
    {
      key: 'reset-api-key',
      label: '重置 API Key',
      icon: <KeyOutlined />,
      onClick: () => onResetApiKey(record.tenant_id),
    },
  ];

  const columns: ColumnsType<TenantInfo> = [
    {
      title: '公司名称',
      dataIndex: 'company_name',
      key: 'company_name',
      width: 200,
      ellipsis: true,
      render: (text, record) => (
        <Link href={`/tenants/${record.tenant_id}`} className="text-blue-600 hover:text-blue-800">
          {text}
        </Link>
      ),
    },
    {
      title: '联系人',
      dataIndex: 'contact_name',
      key: 'contact_name',
      width: 120,
      ellipsis: true,
    },
    {
      title: '联系邮箱',
      dataIndex: 'contact_email',
      key: 'contact_email',
      width: 200,
      ellipsis: true,
    },
    {
      title: '联系电话',
      dataIndex: 'contact_phone',
      key: 'contact_phone',
      width: 140,
      render: (text) => text || '-',
    },
    {
      title: '套餐',
      dataIndex: 'current_plan',
      key: 'current_plan',
      width: 100,
      render: (plan: string) => {
        const config = planConfig[plan] || { color: 'default', label: plan };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
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
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Link href={`/tenants/${record.tenant_id}`}>
              <Button type="text" size="small" icon={<EyeOutlined />} />
            </Link>
          </Tooltip>
          <Dropdown menu={{ items: getActionMenu(record) }} trigger={['click']}>
            <Button type="text" size="small" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  const rowSelection = onSelectChange
    ? {
        selectedRowKeys,
        onChange: (keys: React.Key[]) => onSelectChange(keys as string[]),
      }
    : undefined;

  return (
    <Table
      dataSource={tenants}
      columns={columns}
      rowKey="tenant_id"
      loading={loading}
      rowSelection={rowSelection}
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

'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, Table, Tag, Button, Space, Modal, message, Typography, InputNumber, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { SendOutlined, ReloadOutlined, AlertOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { adminTenantsApi } from '@/lib/api/admin';
import { OverdueTenantInfo } from '@/types/admin';

const { Title, Text } = Typography;

export default function OverdueTenantsPage() {
  const [loading, setLoading] = useState(true);
  const [tenants, setTenants] = useState<OverdueTenantInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [minDaysOverdue, setMinDaysOverdue] = useState(0);

  const fetchOverdueTenants = useCallback(async () => {
    setLoading(true);
    try {
      const response = await adminTenantsApi.getOverdue(page, pageSize, minDaysOverdue);
      if (response.success && response.data) {
        setTenants(response.data.items);
        setTotal(response.data.total);
      }
    } catch (error) {
      console.error('Failed to fetch overdue tenants:', error);
      message.error('加载欠费租户列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, minDaysOverdue]);

  useEffect(() => {
    fetchOverdueTenants();
  }, [fetchOverdueTenants]);

  const handleSendReminder = async (tenantId: string) => {
    Modal.confirm({
      title: '发送催款提醒',
      content: '确认向该租户发送催款提醒？',
      onOk: async () => {
        try {
          const response = await adminTenantsApi.sendReminder(tenantId);
          if (response.success) {
            message.success('催款提醒已发送');
          } else {
            message.error(response.error?.message || '发送失败');
          }
        } catch {
          message.error('发送失败');
        }
      },
    });
  };

  const columns: ColumnsType<OverdueTenantInfo> = [
    {
      title: '公司名称',
      dataIndex: 'company_name',
      key: 'company_name',
      width: 200,
      render: (text, record) => (
        <Link href={`/tenants/${record.tenant_id}`} className="text-blue-600">
          {text}
        </Link>
      ),
    },
    {
      title: '联系人',
      dataIndex: 'contact_name',
      key: 'contact_name',
      width: 120,
      render: (text) => text || '-',
    },
    {
      title: '联系邮箱',
      dataIndex: 'email',
      key: 'email',
      width: 200,
    },
    {
      title: '欠费金额',
      dataIndex: 'total_overdue',
      key: 'total_overdue',
      width: 120,
      render: (amount: number) => (
        <Text type="danger" strong>¥{amount.toFixed(2)}</Text>
      ),
      sorter: (a, b) => a.total_overdue - b.total_overdue,
    },
    {
      title: '逾期天数',
      dataIndex: 'days_overdue',
      key: 'days_overdue',
      width: 100,
      render: (days: number) => {
        let color = 'gold';
        if (days > 30) color = 'red';
        else if (days > 14) color = 'orange';
        return <Tag color={color}>{days} 天</Tag>;
      },
      sorter: (a, b) => a.days_overdue - b.days_overdue,
    },
    {
      title: '欠费账单数',
      dataIndex: 'overdue_bills_count',
      key: 'overdue_bills_count',
      width: 100,
    },
    {
      title: '最早到期日',
      dataIndex: 'oldest_due_date',
      key: 'oldest_due_date',
      width: 120,
      render: (date: string) => new Date(date).toLocaleDateString('zh-CN'),
    },
    {
      title: '降级状态',
      dataIndex: 'degradation_level',
      key: 'degradation_level',
      width: 100,
      render: (level: string | null) => {
        if (!level) return <Tag>正常</Tag>;
        const colors: Record<string, string> = {
          warning: 'orange',
          limited: 'red',
          suspended: 'default',
        };
        const labels: Record<string, string> = {
          warning: '警告',
          limited: '限制',
          suspended: '已停用',
        };
        return <Tag color={colors[level]}>{labels[level] || level}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="发送催款提醒">
            <Button
              type="link"
              size="small"
              icon={<SendOutlined />}
              onClick={() => handleSendReminder(record.tenant_id)}
            >
              催款
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <AlertOutlined className="text-red-500 text-xl" />
          <Title level={4} className="mb-0">欠费租户</Title>
        </div>
      </div>

      <Card>
        {/* Filters */}
        <div className="mb-4 flex gap-4 items-center">
          <span>最小逾期天数：</span>
          <InputNumber
            min={0}
            value={minDaysOverdue}
            onChange={(value) => setMinDaysOverdue(value || 0)}
            style={{ width: 100 }}
          />
          <Button type="primary" onClick={fetchOverdueTenants}>
            筛选
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchOverdueTenants}>
            刷新
          </Button>
        </div>

        {/* Summary */}
        {tenants.length > 0 && (
          <div className="mb-4 p-4 bg-red-50 rounded flex gap-8">
            <div>
              <Text type="secondary">欠费租户数</Text>
              <div className="text-2xl font-bold text-red-500">{total}</div>
            </div>
            <div>
              <Text type="secondary">总欠费金额</Text>
              <div className="text-2xl font-bold text-red-500">
                ¥{tenants.reduce((sum, t) => sum + t.total_overdue, 0).toFixed(2)}
              </div>
            </div>
          </div>
        )}

        {/* Table */}
        <Table
          dataSource={tenants}
          columns={columns}
          rowKey="tenant_id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
}

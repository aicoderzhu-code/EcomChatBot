'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, Table, Tag, Select, Button, Space, message, Typography, Row, Col, Statistic } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  AlertOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { adminAuditApi } from '@/lib/api/admin';
import { SecurityAlert, AuditStatistics } from '@/types/admin';

const { Title } = Typography;

const severityOptions = [
  { value: '', label: '全部级别' },
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
  { value: 'critical', label: '严重' },
];

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'new', label: '新告警' },
  { value: 'investigating', label: '处理中' },
  { value: 'resolved', label: '已解决' },
  { value: 'dismissed', label: '已忽略' },
];

const severityConfig: Record<string, { color: string; label: string }> = {
  low: { color: 'blue', label: '低' },
  medium: { color: 'orange', label: '中' },
  high: { color: 'red', label: '高' },
  critical: { color: 'magenta', label: '严重' },
};

const statusConfig: Record<string, { color: string; label: string }> = {
  new: { color: 'red', label: '新告警' },
  investigating: { color: 'orange', label: '处理中' },
  resolved: { color: 'green', label: '已解决' },
  dismissed: { color: 'default', label: '已忽略' },
};

export default function SecurityAuditPage() {
  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [severity, setSeverity] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [statistics, setStatistics] = useState<AuditStatistics | null>(null);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const response = await adminAuditApi.getSecurityAlerts(
        page,
        pageSize,
        severity || undefined,
        status || undefined
      );
      if (response.success && response.data) {
        setAlerts(response.data.items);
        setTotal(response.data.total);
      }
    } catch (error) {
      console.error('Failed to fetch security alerts:', error);
      message.error('加载安全告警失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, severity, status]);

  const fetchStatistics = async () => {
    try {
      const response = await adminAuditApi.getStatistics();
      if (response.success && response.data) {
        setStatistics(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch audit statistics:', error);
    }
  };

  useEffect(() => {
    fetchAlerts();
    fetchStatistics();
  }, [fetchAlerts]);

  const handleUpdateStatus = async (alertId: string, newStatus: 'investigating' | 'resolved' | 'dismissed') => {
    try {
      const response = await adminAuditApi.updateAlertStatus(alertId, newStatus);
      if (response.success) {
        message.success('状态更新成功');
        fetchAlerts();
        fetchStatistics();
      } else {
        message.error(response.error?.message || '操作失败');
      }
    } catch {
      message.error('操作失败');
    }
  };

  const columns: ColumnsType<SecurityAlert> = [
    {
      title: '告警时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '告警类型',
      dataIndex: 'alert_type',
      key: 'alert_type',
      width: 150,
    },
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (sev: string) => {
        const config = severityConfig[sev] || { color: 'default', label: sev };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '来源 IP',
      dataIndex: 'source_ip',
      key: 'source_ip',
      width: 140,
      render: (ip: string | null) => ip || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (st: string) => {
        const config = statusConfig[st] || { color: 'default', label: st };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          {record.status === 'new' && (
            <Button
              type="link"
              size="small"
              icon={<ExclamationCircleOutlined />}
              onClick={() => handleUpdateStatus(record.alert_id, 'investigating')}
            >
              处理
            </Button>
          )}
          {record.status === 'investigating' && (
            <>
              <Button
                type="link"
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => handleUpdateStatus(record.alert_id, 'resolved')}
              >
                解决
              </Button>
              <Button
                type="link"
                size="small"
                icon={<CloseCircleOutlined />}
                onClick={() => handleUpdateStatus(record.alert_id, 'dismissed')}
              >
                忽略
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <AlertOutlined className="text-red-500 text-xl" />
        <Title level={4} className="mb-0">安全审计</Title>
      </div>

      {/* Statistics cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="今日操作"
              value={statistics?.operations_today || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="安全告警"
              value={statistics?.security_alerts || 0}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="高危操作"
              value={statistics?.high_risk_operations || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="总操作数"
              value={statistics?.total_operations || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        {/* Filters */}
        <div className="mb-4 flex flex-wrap gap-4">
          <Select
            value={severity}
            onChange={setSeverity}
            options={severityOptions}
            style={{ width: 140 }}
            placeholder="告警级别"
          />
          <Select
            value={status}
            onChange={setStatus}
            options={statusOptions}
            style={{ width: 140 }}
            placeholder="状态"
          />
          <Button type="primary" onClick={fetchAlerts}>
            搜索
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => { fetchAlerts(); fetchStatistics(); }}>
            刷新
          </Button>
        </div>

        {/* Alerts table */}
        <Table
          dataSource={alerts}
          columns={columns}
          rowKey="alert_id"
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
          scroll={{ x: 1100 }}
        />
      </Card>
    </div>
  );
}

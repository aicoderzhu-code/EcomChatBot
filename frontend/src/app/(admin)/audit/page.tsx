'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, Select, DatePicker, Button, Modal, Descriptions, Typography, message } from 'antd';
import type { Dayjs } from 'dayjs';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { AuditLogTable } from '@/components/admin/audit';
import { adminAuditApi } from '@/lib/api/admin';
import { AuditLog, AuditLogQueryParams } from '@/types/admin';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const operationTypeOptions = [
  { value: '', label: '全部操作' },
  { value: 'tenant_create', label: '创建租户' },
  { value: 'tenant_update', label: '更新租户' },
  { value: 'tenant_delete', label: '删除租户' },
  { value: 'plan_change', label: '套餐变更' },
  { value: 'quota_adjustment', label: '配额调整' },
  { value: 'reset_api_key', label: '重置API Key' },
  { value: 'approve_bill', label: '审核账单' },
  { value: 'admin_create', label: '创建管理员' },
  { value: 'admin_update', label: '更新管理员' },
  { value: 'batch_operation', label: '批量操作' },
];

const resourceTypeOptions = [
  { value: '', label: '全部资源' },
  { value: 'tenant', label: '租户' },
  { value: 'subscription', label: '订阅' },
  { value: 'admin', label: '管理员' },
  { value: 'bill', label: '账单' },
  { value: 'system', label: '系统' },
];

export default function AuditPage() {
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [operationType, setOperationType] = useState<string>('');
  const [resourceType, setResourceType] = useState<string>('');
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params: AuditLogQueryParams = {
        page,
        size: pageSize,
        operation_type: operationType || undefined,
        resource_type: resourceType || undefined,
        start_date: dateRange?.[0]?.format('YYYY-MM-DD') || undefined,
        end_date: dateRange?.[1]?.format('YYYY-MM-DD') || undefined,
      };

      const response = await adminAuditApi.getLogs(params);
      if (response.success && response.data) {
        setLogs(response.data.items);
        setTotal(response.data.total);
      }
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
      message.error('加载审计日志失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, operationType, resourceType, dateRange]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleSearch = () => {
    setPage(1);
    fetchLogs();
  };

  const handleViewDetails = (log: AuditLog) => {
    setSelectedLog(log);
    setDetailModalOpen(true);
  };

  return (
    <div className="space-y-4">
      <Title level={4}>操作日志</Title>

      <Card>
        {/* Filters */}
        <div className="mb-4 flex flex-wrap gap-4">
          <Select
            value={operationType}
            onChange={setOperationType}
            options={operationTypeOptions}
            style={{ width: 160 }}
            placeholder="操作类型"
          />
          <Select
            value={resourceType}
            onChange={setResourceType}
            options={resourceTypeOptions}
            style={{ width: 140 }}
            placeholder="资源类型"
          />
          <RangePicker
            value={dateRange}
            onChange={(dates) => setDateRange(dates)}
            placeholder={['开始日期', '结束日期']}
          />
          <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
            搜索
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchLogs}>
            刷新
          </Button>
        </div>

        {/* Table */}
        <AuditLogTable
          logs={logs}
          loading={loading}
          total={total}
          page={page}
          pageSize={pageSize}
          onPageChange={(p, ps) => {
            setPage(p);
            setPageSize(ps);
          }}
          onViewDetails={handleViewDetails}
        />
      </Card>

      {/* Detail modal */}
      <Modal
        title="操作详情"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={null}
        width={600}
      >
        {selectedLog && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="日志 ID">{selectedLog.log_id}</Descriptions.Item>
            <Descriptions.Item label="操作时间">
              {new Date(selectedLog.created_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
            <Descriptions.Item label="操作人">
              {selectedLog.admin_username || selectedLog.admin_id}
            </Descriptions.Item>
            <Descriptions.Item label="操作类型">{selectedLog.operation_type}</Descriptions.Item>
            <Descriptions.Item label="资源类型">{selectedLog.resource_type}</Descriptions.Item>
            <Descriptions.Item label="资源 ID">{selectedLog.resource_id}</Descriptions.Item>
            <Descriptions.Item label="IP 地址">{selectedLog.ip_address || '-'}</Descriptions.Item>
            <Descriptions.Item label="User Agent">
              <Text className="text-xs">{selectedLog.user_agent || '-'}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="操作详情">
              <pre className="bg-gray-50 p-2 rounded text-xs overflow-auto max-h-40">
                {JSON.stringify(selectedLog.operation_details, null, 2)}
              </pre>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}

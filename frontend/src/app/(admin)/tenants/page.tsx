'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, Input, Select, Button, Space, Modal, message, Typography, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import {
  SearchOutlined,
  PlusOutlined,
  ReloadOutlined,
  DownOutlined,
} from '@ant-design/icons';
import { TenantTable, TenantCreateModal } from '@/components/admin/tenants';
import { adminTenantsApi } from '@/lib/api/admin';
import { TenantInfo, TenantStatus, TenantQueryParams, BatchOperation } from '@/types/admin';

const { Title } = Typography;

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '正常' },
  { value: 'suspended', label: '已停用' },
  { value: 'pending', label: '待激活' },
];

const planOptions = [
  { value: '', label: '全部套餐' },
  { value: 'free', label: '免费版' },
  { value: 'basic', label: '基础版' },
  { value: 'professional', label: '专业版' },
  { value: 'enterprise', label: '企业版' },
];

export default function TenantsPage() {
  const [loading, setLoading] = useState(true);
  const [tenants, setTenants] = useState<TenantInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState<string>('');
  const [plan, setPlan] = useState<string>('');
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);

  const fetchTenants = useCallback(async () => {
    setLoading(true);
    try {
      const params: TenantQueryParams = {
        page,
        size: pageSize,
        keyword: keyword || undefined,
        status: (status as TenantStatus) || undefined,
        plan: plan || undefined,
      };

      const response = await adminTenantsApi.list(params);
      if (response.success && response.data) {
        setTenants(response.data.items);
        setTotal(response.data.total);
      }
    } catch (error) {
      console.error('Failed to fetch tenants:', error);
      message.error('加载租户列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, keyword, status, plan]);

  useEffect(() => {
    fetchTenants();
  }, [fetchTenants]);

  const handleSearch = () => {
    setPage(1);
    fetchTenants();
  };

  const handlePageChange = (newPage: number, newPageSize: number) => {
    setPage(newPage);
    setPageSize(newPageSize);
  };

  const handleStatusChange = async (tenantId: string, newStatus: TenantStatus) => {
    Modal.confirm({
      title: `确认${newStatus === 'active' ? '启用' : '停用'}租户？`,
      content: newStatus === 'suspended' ? '停用后租户将无法使用系统服务' : '启用后租户将恢复正常使用',
      onOk: async () => {
        try {
          const response = await adminTenantsApi.updateStatus(tenantId, {
            status: newStatus,
            reason: newStatus === 'suspended' ? '管理员手动停用' : '管理员手动启用',
          });
          if (response.success) {
            message.success('状态更新成功');
            fetchTenants();
          } else {
            message.error(response.error?.message || '操作失败');
          }
        } catch {
          message.error('操作失败');
        }
      },
    });
  };

  const handleResetApiKey = async (tenantId: string) => {
    Modal.confirm({
      title: '确认重置 API Key？',
      content: '重置后原有的 API Key 将立即失效，请确保通知租户更新配置',
      onOk: async () => {
        try {
          const response = await adminTenantsApi.resetApiKey(tenantId);
          if (response.success && response.data) {
            Modal.success({
              title: 'API Key 已重置',
              content: (
                <div>
                  <p>新的 API Key（仅显示一次）：</p>
                  <code className="block bg-gray-100 p-2 mt-2 break-all">
                    {response.data.api_key}
                  </code>
                </div>
              ),
              width: 500,
            });
          } else {
            message.error(response.error?.message || '重置失败');
          }
        } catch {
          message.error('重置失败');
        }
      },
    });
  };

  const handleBatchOperation = async (operation: BatchOperation, params?: Record<string, unknown>) => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择租户');
      return;
    }

    const operationLabels: Record<string, string> = {
      activate: '批量启用',
      suspend: '批量停用',
      delete: '批量删除',
      reset_quota: '批量重置配额',
    };

    Modal.confirm({
      title: `确认${operationLabels[operation]}？`,
      content: `将对选中的 ${selectedRowKeys.length} 个租户执行操作`,
      onOk: async () => {
        try {
          const response = await adminTenantsApi.batchOperation({
            tenant_ids: selectedRowKeys,
            operation,
            params,
          });
          if (response.success && response.data) {
            message.success(
              `操作完成：成功 ${response.data.success_count} 个，失败 ${response.data.failed_count} 个`
            );
            setSelectedRowKeys([]);
            fetchTenants();
          } else {
            message.error(response.error?.message || '操作失败');
          }
        } catch {
          message.error('操作失败');
        }
      },
    });
  };

  const batchMenuItems: MenuProps['items'] = [
    { key: 'activate', label: '批量启用', onClick: () => handleBatchOperation('activate') },
    { key: 'suspend', label: '批量停用', onClick: () => handleBatchOperation('suspend') },
    { key: 'reset_quota', label: '批量重置配额', onClick: () => handleBatchOperation('reset_quota') },
    { type: 'divider' },
    { key: 'delete', label: '批量删除', danger: true, onClick: () => handleBatchOperation('delete') },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <Title level={4} className="mb-0">租户管理</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateModalOpen(true)}
        >
          创建租户
        </Button>
      </div>

      <Card>
        {/* Search filters */}
        <div className="mb-4 flex flex-wrap gap-4">
          <Input
            placeholder="搜索公司名称/邮箱"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 240 }}
            allowClear
          />
          <Select
            value={status}
            onChange={setStatus}
            options={statusOptions}
            style={{ width: 140 }}
          />
          <Select
            value={plan}
            onChange={setPlan}
            options={planOptions}
            style={{ width: 140 }}
          />
          <Button type="primary" onClick={handleSearch}>
            搜索
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchTenants}>
            刷新
          </Button>

          {selectedRowKeys.length > 0 && (
            <Dropdown menu={{ items: batchMenuItems }}>
              <Button>
                <Space>
                  批量操作 ({selectedRowKeys.length})
                  <DownOutlined />
                </Space>
              </Button>
            </Dropdown>
          )}
        </div>

        {/* Tenant table */}
        <TenantTable
          tenants={tenants}
          loading={loading}
          total={total}
          page={page}
          pageSize={pageSize}
          onPageChange={handlePageChange}
          onStatusChange={handleStatusChange}
          onResetApiKey={handleResetApiKey}
          selectedRowKeys={selectedRowKeys}
          onSelectChange={setSelectedRowKeys}
        />
      </Card>

      {/* Create modal */}
      <TenantCreateModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSuccess={() => {
          fetchTenants();
        }}
      />
    </div>
  );
}

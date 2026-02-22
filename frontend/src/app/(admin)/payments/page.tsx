'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, Select, Input, Button, Typography, message } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { OrderTable } from '@/components/admin/payments';
import { adminPaymentsApi } from '@/lib/api/admin';
import { PaymentOrderInfo } from '@/types/admin';

const { Title } = Typography;

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'pending', label: '待支付' },
  { value: 'paid', label: '已支付' },
  { value: 'failed', label: '支付失败' },
  { value: 'refunded', label: '已退款' },
  { value: 'cancelled', label: '已取消' },
];

export default function PaymentsPage() {
  const [loading, setLoading] = useState(true);
  const [orders, setOrders] = useState<PaymentOrderInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [status, setStatus] = useState<string>('');
  const [tenantId, setTenantId] = useState<string>('');

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const response = await adminPaymentsApi.listOrders({
        page,
        size: pageSize,
        status: status || undefined,
        tenant_id: tenantId || undefined,
      });
      if (response.success && response.data) {
        setOrders(response.data.items);
        setTotal(response.data.total);
      }
    } catch (error) {
      console.error('Failed to fetch orders:', error);
      message.error('加载订单列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, status, tenantId]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleSearch = () => {
    setPage(1);
    fetchOrders();
  };

  const handlePageChange = (newPage: number, newPageSize: number) => {
    setPage(newPage);
    setPageSize(newPageSize);
  };

  return (
    <div className="space-y-4">
      <Title level={4}>支付订单</Title>

      <Card>
        {/* Search filters */}
        <div className="mb-4 flex flex-wrap gap-4">
          <Input
            placeholder="租户 ID"
            prefix={<SearchOutlined />}
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 200 }}
            allowClear
          />
          <Select
            value={status}
            onChange={setStatus}
            options={statusOptions}
            style={{ width: 140 }}
          />
          <Button type="primary" onClick={handleSearch}>
            搜索
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchOrders}>
            刷新
          </Button>
        </div>

        {/* Order table */}
        <OrderTable
          orders={orders}
          loading={loading}
          total={total}
          page={page}
          pageSize={pageSize}
          onPageChange={handlePageChange}
        />
      </Card>
    </div>
  );
}

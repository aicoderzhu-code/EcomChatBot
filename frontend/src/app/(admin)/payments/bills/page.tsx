'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, Tabs, Modal, Input, message, Typography } from 'antd';
import type { TabsProps } from 'antd';
import { BillTable } from '@/components/admin/payments';
import { adminPaymentsApi } from '@/lib/api/admin';
import { PendingBillInfo, BillInfo } from '@/types/admin';

const { Title } = Typography;
const { TextArea } = Input;

export default function BillsPage() {
  const [activeTab, setActiveTab] = useState('pending');
  const [pendingLoading, setPendingLoading] = useState(true);
  const [allLoading, setAllLoading] = useState(false);
  const [pendingBills, setPendingBills] = useState<PendingBillInfo[]>([]);
  const [allBills, setAllBills] = useState<BillInfo[]>([]);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [allTotal, setAllTotal] = useState(0);
  const [pendingPage, setPendingPage] = useState(1);
  const [allPage, setAllPage] = useState(1);
  const [pageSize] = useState(20);

  const fetchPendingBills = useCallback(async () => {
    setPendingLoading(true);
    try {
      const response = await adminPaymentsApi.getPendingBills(pendingPage, pageSize);
      if (response.success && response.data) {
        setPendingBills(response.data.items);
        setPendingTotal(response.data.total);
      }
    } catch (error) {
      console.error('Failed to fetch pending bills:', error);
      message.error('加载待审核账单失败');
    } finally {
      setPendingLoading(false);
    }
  }, [pendingPage, pageSize]);

  const fetchAllBills = useCallback(async () => {
    setAllLoading(true);
    try {
      const response = await adminPaymentsApi.listBills({
        page: allPage,
        page_size: pageSize,
      });
      if (response.success && response.data) {
        setAllBills(response.data.items);
        setAllTotal(response.data.total);
      }
    } catch (error) {
      console.error('Failed to fetch all bills:', error);
      message.error('加载账单列表失败');
    } finally {
      setAllLoading(false);
    }
  }, [allPage, pageSize]);

  useEffect(() => {
    if (activeTab === 'pending') {
      fetchPendingBills();
    } else {
      fetchAllBills();
    }
  }, [activeTab, fetchPendingBills, fetchAllBills]);

  const handleApprove = async (billId: string) => {
    Modal.confirm({
      title: '确认审核通过？',
      content: '账单审核通过后将等待租户支付',
      onOk: async () => {
        try {
          const response = await adminPaymentsApi.approveBill(billId);
          if (response.success) {
            message.success('账单审核通过');
            fetchPendingBills();
          } else {
            message.error(response.error?.message || '操作失败');
          }
        } catch {
          message.error('操作失败');
        }
      },
    });
  };

  const handleReject = async (billId: string) => {
    let reason = '';
    Modal.confirm({
      title: '拒绝账单',
      content: (
        <div>
          <p className="mb-2">请输入拒绝原因：</p>
          <TextArea
            rows={3}
            onChange={(e) => { reason = e.target.value; }}
            placeholder="请输入拒绝原因"
          />
        </div>
      ),
      onOk: async () => {
        if (!reason.trim()) {
          message.warning('请输入拒绝原因');
          return Promise.reject();
        }
        try {
          const response = await adminPaymentsApi.rejectBill(billId, reason);
          if (response.success) {
            message.success('账单已拒绝');
            fetchPendingBills();
          } else {
            message.error(response.error?.message || '操作失败');
          }
        } catch {
          message.error('操作失败');
        }
      },
    });
  };

  const tabItems: TabsProps['items'] = [
    {
      key: 'pending',
      label: `待审核 (${pendingTotal})`,
      children: (
        <BillTable
          bills={pendingBills}
          loading={pendingLoading}
          total={pendingTotal}
          page={pendingPage}
          pageSize={pageSize}
          onPageChange={(p) => setPendingPage(p)}
          onApprove={handleApprove}
          onReject={handleReject}
          showActions
        />
      ),
    },
    {
      key: 'all',
      label: '全部账单',
      children: (
        <BillTable
          bills={allBills}
          loading={allLoading}
          total={allTotal}
          page={allPage}
          pageSize={pageSize}
          onPageChange={(p) => setAllPage(p)}
        />
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <Title level={4}>账单管理</Title>

      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Card>
    </div>
  );
}

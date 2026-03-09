'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Tag, Button, Space, Modal, Input, Row, Col,
  Statistic, message, Popconfirm, Tooltip, Select,
} from 'antd';
import {
  CheckOutlined, CloseOutlined, ThunderboltOutlined,
  FileTextOutlined, CheckCircleOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  knowledgeExtractionApi,
  KnowledgeCandidate,
  ExtractionMetrics,
} from '@/lib/api/knowledgeExtraction';

const { TextArea } = Input;

export default function CandidateReviewQueue() {
  const [candidates, setCandidates] = useState<KnowledgeCandidate[]>([]);
  const [metrics, setMetrics] = useState<ExtractionMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Reject modal
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectingId, setRejectingId] = useState<string>('');
  const [rejectReason, setRejectReason] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [listResp, metricsResp] = await Promise.all([
        knowledgeExtractionApi.listCandidates({
          status: statusFilter || undefined,
          page: pagination.current,
          size: pagination.pageSize,
        }),
        knowledgeExtractionApi.getMetrics(),
      ]);
      if (listResp.success && listResp.data) {
        setCandidates(listResp.data.items);
        setPagination(prev => ({ ...prev, total: listResp.data!.total }));
      }
      if (metricsResp.success) setMetrics(metricsResp.data);
    } catch {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, pagination.current, pagination.pageSize]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleApprove = async (candidateId: string) => {
    try {
      await knowledgeExtractionApi.approve(candidateId);
      message.success('已通过并创建 QA 对');
      loadData();
    } catch {
      message.error('操作失败');
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      message.warning('请输入拒绝原因');
      return;
    }
    try {
      await knowledgeExtractionApi.reject(rejectingId, rejectReason);
      message.success('已拒绝');
      setRejectOpen(false);
      setRejectReason('');
      loadData();
    } catch {
      message.error('操作失败');
    }
  };

  const handleBatchApprove = async () => {
    if (selectedIds.length === 0) return;
    try {
      const resp = await knowledgeExtractionApi.batchApprove(selectedIds);
      if (resp.success && resp.data) {
        message.success(`批量通过 ${resp.data.success.length} 条`);
        setSelectedIds([]);
        loadData();
      }
    } catch {
      message.error('批量操作失败');
    }
  };

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'pending': return <Tag icon={<ClockCircleOutlined />} color="processing">待审核</Tag>;
      case 'approved': return <Tag icon={<CheckCircleOutlined />} color="success">已通过</Tag>;
      case 'rejected': return <Tag color="error">已拒绝</Tag>;
      default: return <Tag>{status}</Tag>;
    }
  };

  const columns: ColumnsType<KnowledgeCandidate> = [
    {
      title: '问题',
      dataIndex: 'question',
      width: 250,
      ellipsis: true,
    },
    {
      title: '答案',
      dataIndex: 'answer',
      width: 300,
      ellipsis: true,
    },
    {
      title: '分类',
      dataIndex: 'category',
      width: 80,
      render: (v: string | null) => v ? <Tag>{v}</Tag> : '-',
    },
    {
      title: '置信度',
      dataIndex: 'confidence_score',
      width: 90,
      sorter: (a, b) => a.confidence_score - b.confidence_score,
      render: (v: number) => (
        <Tag color={v >= 0.8 ? 'green' : v >= 0.6 ? 'orange' : 'red'}>
          {(v * 100).toFixed(0)}%
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: getStatusTag,
    },
    {
      title: '操作',
      width: 150,
      render: (_, record) => record.status === 'pending' ? (
        <Space size="small">
          <Tooltip title="通过">
            <Popconfirm title="确定通过？将自动创建 QA 对" onConfirm={() => handleApprove(record.candidate_id)}>
              <Button size="small" type="primary" icon={<CheckOutlined />} />
            </Popconfirm>
          </Tooltip>
          <Tooltip title="拒绝">
            <Button
              size="small"
              danger
              icon={<CloseOutlined />}
              onClick={() => {
                setRejectingId(record.candidate_id);
                setRejectOpen(true);
              }}
            />
          </Tooltip>
        </Space>
      ) : (
        record.rejection_reason ? (
          <Tooltip title={record.rejection_reason}>
            <span style={{ color: '#999', fontSize: 12 }}>查看原因</span>
          </Tooltip>
        ) : null
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* 统计 */}
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="总提取数" value={metrics?.total || 0} prefix={<ThunderboltOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="待审核" value={metrics?.pending || 0} prefix={<ClockCircleOutlined />} valueStyle={{ color: '#1890ff' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="已通过" value={metrics?.approved || 0} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="通过率" value={metrics?.approval_rate || 0} suffix="%" prefix={<FileTextOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* 列表 */}
      <Card
        title="候选知识审核"
        extra={
          <Space>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 120 }}
              options={[
                { label: '待审核', value: 'pending' },
                { label: '已通过', value: 'approved' },
                { label: '已拒绝', value: 'rejected' },
                { label: '全部', value: '' },
              ]}
            />
            {selectedIds.length > 0 && (
              <Button type="primary" onClick={handleBatchApprove}>
                批量通过 ({selectedIds.length})
              </Button>
            )}
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={candidates}
          rowKey="candidate_id"
          loading={loading}
          rowSelection={
            statusFilter === 'pending' ? {
              selectedRowKeys: selectedIds,
              onChange: (keys) => setSelectedIds(keys as string[]),
            } : undefined
          }
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: total => `共 ${total} 条`,
            onChange: (page, pageSize) => setPagination(prev => ({ ...prev, current: page, pageSize })),
          }}
        />
      </Card>

      {/* 拒绝弹窗 */}
      <Modal
        title="拒绝原因"
        open={rejectOpen}
        onOk={handleReject}
        onCancel={() => { setRejectOpen(false); setRejectReason(''); }}
      >
        <TextArea
          rows={3}
          value={rejectReason}
          onChange={e => setRejectReason(e.target.value)}
          placeholder="请输入拒绝原因..."
        />
      </Modal>
    </div>
  );
}

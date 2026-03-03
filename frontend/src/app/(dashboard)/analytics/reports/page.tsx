'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Select, Space, Tag, message, Modal, Typography,
  Form, Input, DatePicker, Descriptions, Row, Col, Statistic, Popconfirm, Empty,
} from 'antd';
import {
  PlusOutlined, FundOutlined, ReloadOutlined,
  DeleteOutlined, EyeOutlined, RocketOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { analyticsApi } from '@/lib/api/analytics';
import type { AnalysisReport } from '@/lib/api/analytics';
import dayjs from 'dayjs';

const { Title, Text, Paragraph } = Typography;
const { RangePicker } = DatePicker;

const reportTypeMap: Record<string, { label: string; color: string }> = {
  daily: { label: '日报', color: 'blue' },
  weekly: { label: '周报', color: 'cyan' },
  monthly: { label: '月报', color: 'purple' },
  custom: { label: '自定义', color: 'geekblue' },
};

const statusMap: Record<string, { label: string; color: string }> = {
  pending: { label: '待生成', color: 'default' },
  generating: { label: '生成中', color: 'processing' },
  completed: { label: '已完成', color: 'success' },
  failed: { label: '失败', color: 'error' },
};

export default function ReportsPage() {
  const [reports, setReports] = useState<AnalysisReport[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size] = useState(20);
  const [loading, setLoading] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();

  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<AnalysisReport | null>(null);
  const [generatingId, setGeneratingId] = useState<number | null>(null);

  const loadReports = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await analyticsApi.listReports({
        report_type: typeFilter,
        status: statusFilter,
        page,
        size,
      });
      if (resp.success && resp.data) {
        setReports(resp.data.items);
        setTotal(resp.data.total);
      }
    } catch {
      message.error('加载报告列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, size, typeFilter, statusFilter]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const handleCreate = async (values: {
    report_type: string;
    title: string;
    period?: [dayjs.Dayjs, dayjs.Dayjs];
  }) => {
    setCreating(true);
    try {
      const body: {
        report_type: string;
        title: string;
        period_start?: string;
        period_end?: string;
      } = {
        report_type: values.report_type,
        title: values.title,
      };
      if (values.period) {
        body.period_start = values.period[0].format('YYYY-MM-DD');
        body.period_end = values.period[1].format('YYYY-MM-DD');
      }
      const resp = await analyticsApi.createReport(body);
      if (resp.success) {
        message.success('报告已创建');
        setCreateOpen(false);
        form.resetFields();
        loadReports();
      } else {
        message.error('创建失败');
      }
    } catch {
      message.error('创建报告失败');
    } finally {
      setCreating(false);
    }
  };

  const handleGenerate = async (reportId: number) => {
    setGeneratingId(reportId);
    try {
      const resp = await analyticsApi.generateReport(reportId);
      if (resp.success) {
        message.success('报告生成完成');
        loadReports();
      } else {
        message.error(resp.error?.message || '生成失败');
      }
    } catch {
      message.error('生成报告失败');
    } finally {
      setGeneratingId(null);
    }
  };

  const handleDelete = async (reportId: number) => {
    try {
      const resp = await analyticsApi.deleteReport(reportId);
      if (resp.success) {
        message.success('已删除');
        loadReports();
      }
    } catch {
      message.error('删除失败');
    }
  };

  const handleViewDetail = async (reportId: number) => {
    try {
      const resp = await analyticsApi.getReport(reportId);
      if (resp.success && resp.data) {
        setSelectedReport(resp.data);
        setDetailOpen(true);
      }
    } catch {
      message.error('获取报告详情失败');
    }
  };

  const columns: ColumnsType<AnalysisReport> = [
    {
      title: '报告标题',
      dataIndex: 'title',
      ellipsis: true,
      render: (title: string, record) => (
        <a onClick={() => handleViewDetail(record.id)}>{title}</a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'report_type',
      width: 90,
      render: (type: string) => {
        const info = reportTypeMap[type] || { label: type, color: 'default' };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (status: string) => {
        const info = statusMap[status] || { label: status, color: 'default' };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: '统计周期',
      width: 200,
      render: (_: unknown, record: AnalysisReport) => {
        if (record.period_start && record.period_end) {
          return `${record.period_start.slice(0, 10)} ~ ${record.period_end.slice(0, 10)}`;
        }
        return <Text type="secondary">-</Text>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      width: 200,
      render: (_: unknown, record: AnalysisReport) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record.id)}
          >
            查看
          </Button>
          {(record.status === 'pending' || record.status === 'failed') && (
            <Button
              type="link"
              size="small"
              icon={<RocketOutlined />}
              loading={generatingId === record.id}
              onClick={() => handleGenerate(record.id)}
            >
              生成
            </Button>
          )}
          <Popconfirm title="确定删除此报告？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>
            <FundOutlined style={{ marginRight: 8 }} />
            分析报告
          </Title>
        </Col>
        <Col>
          <Space>
            <Select
              allowClear
              placeholder="报告类型"
              style={{ width: 120 }}
              value={typeFilter}
              onChange={(v) => { setTypeFilter(v); setPage(1); }}
              options={[
                { value: 'daily', label: '日报' },
                { value: 'weekly', label: '周报' },
                { value: 'monthly', label: '月报' },
                { value: 'custom', label: '自定义' },
              ]}
            />
            <Select
              allowClear
              placeholder="状态"
              style={{ width: 120 }}
              value={statusFilter}
              onChange={(v) => { setStatusFilter(v); setPage(1); }}
              options={[
                { value: 'pending', label: '待生成' },
                { value: 'generating', label: '生成中' },
                { value: 'completed', label: '已完成' },
                { value: 'failed', label: '失败' },
              ]}
            />
            <Button icon={<ReloadOutlined />} onClick={loadReports}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              创建报告
            </Button>
          </Space>
        </Col>
      </Row>

      <Card>
        <Table
          columns={columns}
          dataSource={reports}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: size,
            total,
            showTotal: (t) => `共 ${t} 条`,
            onChange: setPage,
          }}
          locale={{
            emptyText: (
              <Empty description="暂无分析报告" image={Empty.PRESENTED_IMAGE_SIMPLE}>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
                  创建第一份报告
                </Button>
              </Empty>
            ),
          }}
        />
      </Card>

      <Modal
        title="创建分析报告"
        open={createOpen}
        onCancel={() => { setCreateOpen(false); form.resetFields(); }}
        footer={null}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            name="title"
            label="报告标题"
            rules={[{ required: true, message: '请输入报告标题' }]}
          >
            <Input placeholder="例如：3月第1周销售分析" />
          </Form.Item>
          <Form.Item
            name="report_type"
            label="报告类型"
            rules={[{ required: true, message: '请选择报告类型' }]}
          >
            <Select
              placeholder="选择报告类型"
              options={[
                { value: 'daily', label: '日报' },
                { value: 'weekly', label: '周报' },
                { value: 'monthly', label: '月报' },
                { value: 'custom', label: '自定义周期' },
              ]}
            />
          </Form.Item>
          <Form.Item name="period" label="统计周期（可选）">
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => { setCreateOpen(false); form.resetFields(); }}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={creating}>
                创建
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="报告详情"
        open={detailOpen}
        onCancel={() => { setDetailOpen(false); setSelectedReport(null); }}
        width={720}
        footer={
          selectedReport && (selectedReport.status === 'pending' || selectedReport.status === 'failed') ? (
            <Button
              type="primary"
              icon={<RocketOutlined />}
              loading={generatingId === selectedReport.id}
              onClick={() => handleGenerate(selectedReport.id)}
            >
              生成报告
            </Button>
          ) : null
        }
      >
        {selectedReport && (
          <div>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="标题" span={2}>
                {selectedReport.title}
              </Descriptions.Item>
              <Descriptions.Item label="类型">
                <Tag color={reportTypeMap[selectedReport.report_type]?.color}>
                  {reportTypeMap[selectedReport.report_type]?.label || selectedReport.report_type}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={statusMap[selectedReport.status]?.color}>
                  {statusMap[selectedReport.status]?.label || selectedReport.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="统计周期" span={2}>
                {selectedReport.period_start && selectedReport.period_end
                  ? `${selectedReport.period_start.slice(0, 10)} ~ ${selectedReport.period_end.slice(0, 10)}`
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>
                {dayjs(selectedReport.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            {selectedReport.summary && (
              <Card title="报告摘要" size="small" style={{ marginTop: 16 }}>
                <Paragraph>{selectedReport.summary}</Paragraph>
              </Card>
            )}

            {selectedReport.statistics && Object.keys(selectedReport.statistics).length > 0 && (
              <Card title="关键指标" size="small" style={{ marginTop: 16 }}>
                <Row gutter={16}>
                  {Object.entries(selectedReport.statistics).map(([key, value]) => (
                    <Col span={8} key={key} style={{ marginBottom: 12 }}>
                      <Statistic
                        title={key}
                        value={typeof value === 'number' ? value : String(value)}
                        precision={typeof value === 'number' && !Number.isInteger(value) ? 2 : 0}
                      />
                    </Col>
                  ))}
                </Row>
              </Card>
            )}

            {selectedReport.error_message && (
              <Card size="small" style={{ marginTop: 16 }}>
                <Text type="danger">错误信息：{selectedReport.error_message}</Text>
              </Card>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

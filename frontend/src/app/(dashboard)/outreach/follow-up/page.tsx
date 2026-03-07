'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Tag,
  Space,
  message,
  Statistic,
  Row,
  Col,
  Progress,
  InputNumber,
  Popconfirm,
} from 'antd';
import { PlusOutlined, PlayCircleOutlined, StopOutlined } from '@ant-design/icons';
import { followUpApi } from '@/lib/api/outreach';
import type { FollowUpPlan, FollowUpDashboard } from '@/types';

const { TextArea } = Input;

export default function FollowUpPage() {
  const [loading, setLoading] = useState(false);
  const [plans, setPlans] = useState<FollowUpPlan[]>([]);
  const [dashboard, setDashboard] = useState<FollowUpDashboard | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  const loadDashboard = useCallback(async () => {
    try {
      const resp = await followUpApi.getDashboard();
      if (resp.success && resp.data) {
        setDashboard(resp.data);
      }
    } catch (err) {
      console.error('加载仪表盘失败:', err);
    }
  }, []);

  const loadPlans = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await followUpApi.listPlans({
        status: statusFilter,
        page,
        size: pageSize,
      });
      if (resp.success && resp.data) {
        setPlans(resp.data.items);
        setTotal(resp.data.total);
      }
    } catch {
      message.error('加载跟进计划失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, statusFilter]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    loadPlans();
  }, [loadPlans]);

  const handleCreate = async (values: Record<string, unknown>) => {
    try {
      const resp = await followUpApi.createPlan(values);
      if (resp.success) {
        message.success('创建跟进计划成功');
        setModalVisible(false);
        form.resetFields();
        loadPlans();
        loadDashboard();
      } else {
        message.error(resp.error?.message || '创建失败');
      }
    } catch {
      message.error('创建跟进计划失败');
    }
  };

  const handleExecute = async (id: number) => {
    try {
      const resp = await followUpApi.executePlan(id);
      if (resp.success) {
        message.success('执行成功');
        loadPlans();
      } else {
        message.error(resp.error?.message || '执行失败');
      }
    } catch {
      message.error('执行失败');
    }
  };

  const handleCancel = async (id: number) => {
    try {
      const resp = await followUpApi.cancelPlan(id);
      if (resp.success) {
        message.success('取消成功');
        loadPlans();
        loadDashboard();
      } else {
        message.error(resp.error?.message || '取消失败');
      }
    } catch {
      message.error('取消失败');
    }
  };

  const reasonLabels: Record<string, { text: string; color: string }> = {
    churn_risk: { text: '流失风险', color: 'red' },
    high_potential: { text: '高潜力', color: 'gold' },
    post_purchase: { text: '购后', color: 'blue' },
    reactivation: { text: '召回', color: 'green' },
  };

  const statusLabels: Record<string, { text: string; color: string }> = {
    active: { text: '进行中', color: 'processing' },
    paused: { text: '已暂停', color: 'warning' },
    completed: { text: '已完成', color: 'success' },
    cancelled: { text: '已取消', color: 'default' },
    converted: { text: '已转化', color: 'success' },
  };

  const columns = [
    {
      title: '用户ID',
      dataIndex: 'user_id',
      key: 'user_id',
    },
    {
      title: '跟进原因',
      dataIndex: 'reason',
      key: 'reason',
      render: (reason: string) => {
        const label = reasonLabels[reason] || { text: reason, color: 'default' };
        return <Tag color={label.color}>{label.text}</Tag>;
      },
    },
    {
      title: '进度',
      key: 'progress',
      render: (_: unknown, record: FollowUpPlan) => (
        <div style={{ width: 120 }}>
          <Progress
            percent={Math.round((record.current_step / record.total_steps) * 100)}
            size="small"
            format={() => `${record.current_step}/${record.total_steps}`}
          />
        </div>
      ),
    },
    {
      title: '下次跟进时间',
      dataIndex: 'next_follow_up_at',
      key: 'next_follow_up_at',
      render: (time: string | null) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '间隔(天)',
      dataIndex: 'interval_days',
      key: 'interval_days',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const label = statusLabels[status] || { text: status, color: 'default' };
        return <Tag color={label.color}>{label.text}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: FollowUpPlan) => (
        <Space>
          {record.status === 'active' && (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleExecute(record.id)}
            >
              手动执行
            </Button>
          )}
          {(record.status === 'active' || record.status === 'paused') && (
            <Popconfirm
              title="确定取消此跟进计划吗？"
              onConfirm={() => handleCancel(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" size="small" danger icon={<StopOutlined />}>
                取消
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃计划数"
              value={dashboard?.active_plans || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已完成"
              value={dashboard?.completed_plans || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已转化"
              value={dashboard?.converted_plans || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="转化率"
              value={dashboard?.conversion_rate || 0}
              precision={2}
              suffix="%"
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="定时跟进计划"
        extra={
          <Space>
            <Select
              placeholder="筛选状态"
              style={{ width: 120 }}
              allowClear
              value={statusFilter}
              onChange={setStatusFilter}
            >
              <Select.Option value="active">进行中</Select.Option>
              <Select.Option value="paused">已暂停</Select.Option>
              <Select.Option value="completed">已完成</Select.Option>
              <Select.Option value="cancelled">已取消</Select.Option>
              <Select.Option value="converted">已转化</Select.Option>
            </Select>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
              创建计划
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={plans}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps || 10);
            },
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
          }}
        />
      </Card>

      <Modal
        title="创建跟进计划"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            label="用户ID"
            name="user_id"
            rules={[{ required: true, message: '请输入用户ID' }]}
          >
            <InputNumber style={{ width: '100%' }} placeholder="请输入用户ID" min={1} />
          </Form.Item>

          <Form.Item
            label="跟进原因"
            name="reason"
            rules={[{ required: true, message: '请选择跟进原因' }]}
          >
            <Select placeholder="请选择跟进原因">
              <Select.Option value="churn_risk">流失风险</Select.Option>
              <Select.Option value="high_potential">高潜力</Select.Option>
              <Select.Option value="post_purchase">购后</Select.Option>
              <Select.Option value="reactivation">召回</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="总步骤数"
            name="total_steps"
            rules={[{ required: true, message: '请输入总步骤数' }]}
            initialValue={3}
          >
            <InputNumber style={{ width: '100%' }} placeholder="请输入总步骤数" min={1} max={10} />
          </Form.Item>

          <Form.Item
            label="间隔天数"
            name="interval_days"
            rules={[{ required: true, message: '请输入间隔天数' }]}
            initialValue={3}
          >
            <InputNumber style={{ width: '100%' }} placeholder="请输入间隔天数" min={1} max={30} />
          </Form.Item>

          <Form.Item label="AI上下文" name="ai_context">
            <TextArea
              rows={4}
              placeholder="输入AI生成内容时的上下文信息（JSON格式）"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Input, Select, Space, Tag,
  message, Modal, Form, Popconfirm, Typography, Tooltip,
  Badge,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  ReloadOutlined, EyeOutlined, TeamOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { segmentApi } from '@/lib/api/outreach';
import type { CustomerSegment, SegmentMember } from '@/types';

const { TextArea } = Input;
const { Title } = Typography;

export default function SegmentsPage() {
  const [segments, setSegments] = useState<CustomerSegment[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [loading, setLoading] = useState(false);

  // 创建/编辑弹窗
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSegment, setEditingSegment] = useState<CustomerSegment | null>(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  // 预览
  const [previewLoading, setPreviewLoading] = useState(false);
  const [matchedCount, setMatchedCount] = useState<number | null>(null);

  // 查看成员弹窗
  const [membersOpen, setMembersOpen] = useState(false);
  const [currentSegment, setCurrentSegment] = useState<CustomerSegment | null>(null);
  const [members, setMembers] = useState<SegmentMember[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [membersTotal, setMembersTotal] = useState(0);
  const [membersPage, setMembersPage] = useState(1);

  const loadSegments = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await segmentApi.list({ page, size });
      if (resp.success && resp.data) {
        setSegments(resp.data.items);
        setTotal(resp.data.total);
      }
    } catch {
      message.error('加载分群列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, size]);

  useEffect(() => {
    loadSegments();
  }, [loadSegments]);

  const handleCreate = () => {
    setEditingSegment(null);
    form.resetFields();
    setMatchedCount(null);
    setModalOpen(true);
  };

  const handleEdit = (record: CustomerSegment) => {
    setEditingSegment(record);
    form.setFieldsValue({
      name: record.name,
      description: record.description,
      segment_type: record.segment_type,
      filter_rules: record.filter_rules ? JSON.stringify(record.filter_rules, null, 2) : '',
    });
    setMatchedCount(null);
    setModalOpen(true);
  };

  const handlePreview = async () => {
    try {
      const values = await form.validateFields(['filter_rules']);
      const filterRules = values.filter_rules ? JSON.parse(values.filter_rules) : {};
      setPreviewLoading(true);
      const resp = await segmentApi.preview(filterRules);
      if (resp.success && resp.data) {
        setMatchedCount(resp.data.matched_count);
        message.success(`预览成功，匹配到 ${resp.data.matched_count} 个用户`);
      }
    } catch (error: unknown) {
      if (error instanceof Error && 'errorFields' in error) {
        return;
      }
      message.error('预览失败');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        name: values.name,
        description: values.description,
        segment_type: values.segment_type,
        filter_rules: values.filter_rules ? JSON.parse(values.filter_rules) : null,
      };

      setSubmitting(true);
      const resp = editingSegment
        ? await segmentApi.update(editingSegment.id, payload)
        : await segmentApi.create(payload);

      if (resp.success) {
        message.success(editingSegment ? '更新成功' : '创建成功');
        setModalOpen(false);
        loadSegments();
      }
    } catch (error: unknown) {
      if (error instanceof Error && 'errorFields' in error) {
        return;
      }
      message.error('操作失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      const resp = await segmentApi.delete(id);
      if (resp.success) {
        message.success('删除成功');
        loadSegments();
      }
    } catch {
      message.error('删除失败');
    }
  };

  const handleRefresh = async (record: CustomerSegment) => {
    try {
      const resp = await segmentApi.refresh(record.id);
      if (resp.success) {
        message.success('刷新成功');
        loadSegments();
      }
    } catch {
      message.error('刷新失败');
    }
  };

  const handleViewMembers = async (record: CustomerSegment) => {
    setCurrentSegment(record);
    setMembersPage(1);
    setMembersOpen(true);
    loadMembers(record.id, 1);
  };

  const loadMembers = async (segmentId: number, memberPage: number) => {
    setMembersLoading(true);
    try {
      const resp = await segmentApi.getMembers(segmentId, { page: memberPage, size: 10 });
      if (resp.success && resp.data) {
        setMembers(resp.data.items);
        setMembersTotal(resp.data.total);
      }
    } catch {
      message.error('加载成员列表失败');
    } finally {
      setMembersLoading(false);
    }
  };

  const columns: ColumnsType<CustomerSegment> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: '类型',
      dataIndex: 'segment_type',
      key: 'segment_type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'manual' ? 'blue' : 'green'}>
          {type === 'manual' ? '手动' : '动态'}
        </Tag>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '成员数',
      dataIndex: 'member_count',
      key: 'member_count',
      width: 100,
      render: (count: number) => (
        <Badge count={count} showZero color="blue" />
      ),
    },
    {
      title: '最后刷新',
      dataIndex: 'last_refreshed_at',
      key: 'last_refreshed_at',
      width: 180,
      render: (time: string | null) => time || '-',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: number) => (
        <Tag color={active ? 'success' : 'default'}>
          {active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 240,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          {record.segment_type === 'dynamic' && (
            <Tooltip title="刷新成员">
              <Button
                type="link"
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => handleRefresh(record)}
              />
            </Tooltip>
          )}
          <Tooltip title="查看成员">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewMembers(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确认删除"
            description="删除后无法恢复，确认删除吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const memberColumns: ColumnsType<SegmentMember> = [
    {
      title: '用户ID',
      dataIndex: 'user_id',
      key: 'user_id',
      width: 100,
    },
    {
      title: '昵称',
      dataIndex: 'nickname',
      key: 'nickname',
      render: (name: string | null) => name || '-',
    },
    {
      title: 'VIP等级',
      dataIndex: 'vip_level',
      key: 'vip_level',
      width: 100,
    },
    {
      title: '会话数',
      dataIndex: 'total_conversations',
      key: 'total_conversations',
      width: 100,
    },
    {
      title: '加入时间',
      dataIndex: 'added_at',
      key: 'added_at',
      width: 180,
      render: (time: string | null) => time || '-',
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4} style={{ margin: 0 }}>
            <TeamOutlined /> 客户分群管理
          </Title>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            创建分群
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={segments}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: size,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, s) => {
              setPage(p);
              setSize(s);
            },
          }}
        />
      </Card>

      {/* 创建/编辑弹窗 */}
      <Modal
        title={editingSegment ? '编辑分群' : '创建分群'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={submitting}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ segment_type: 'manual' }}
        >
          <Form.Item
            label="分群名称"
            name="name"
            rules={[{ required: true, message: '请输入分群名称' }]}
          >
            <Input placeholder="请输入分群名称" />
          </Form.Item>

          <Form.Item
            label="描述"
            name="description"
          >
            <TextArea rows={2} placeholder="请输入描述" />
          </Form.Item>

          <Form.Item
            label="分群类型"
            name="segment_type"
            rules={[{ required: true, message: '请选择分群类型' }]}
          >
            <Select>
              <Select.Option value="manual">手动</Select.Option>
              <Select.Option value="dynamic">动态</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.segment_type !== curr.segment_type}
          >
            {({ getFieldValue }) =>
              getFieldValue('segment_type') === 'dynamic' && (
                <>
                  <Form.Item
                    label="筛选规则 (JSON)"
                    name="filter_rules"
                    extra={'示例: {"vip_level_min": 3, "order_count_min": 5, "total_amount_min": 1000, "last_order_days_ago": 30}'}
                  >
                    <TextArea
                      rows={6}
                      placeholder='{"vip_level_min": 3, "order_count_min": 5}'
                    />
                  </Form.Item>

                  <Form.Item>
                    <Space>
                      <Button
                        onClick={handlePreview}
                        loading={previewLoading}
                        icon={<EyeOutlined />}
                      >
                        预览匹配用户
                      </Button>
                      {matchedCount !== null && (
                        <Tag color="blue">匹配到 {matchedCount} 个用户</Tag>
                      )}
                    </Space>
                  </Form.Item>
                </>
              )
            }
          </Form.Item>
        </Form>
      </Modal>

      {/* 查看成员弹窗 */}
      <Modal
        title={`${currentSegment?.name} - 成员列表`}
        open={membersOpen}
        onCancel={() => setMembersOpen(false)}
        footer={null}
        width={900}
      >
        <Table
          columns={memberColumns}
          dataSource={members}
          rowKey="id"
          loading={membersLoading}
          pagination={{
            current: membersPage,
            pageSize: 10,
            total: membersTotal,
            showTotal: (t) => `共 ${t} 个成员`,
            onChange: (p) => {
              setMembersPage(p);
              if (currentSegment) {
                loadMembers(currentSegment.id, p);
              }
            },
          }}
        />
      </Modal>
    </div>
  );
}


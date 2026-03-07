'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Input, Select, Space, Tag,
  message, Modal, Form, Popconfirm, Typography, Switch,
  InputNumber, Row, Col,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { ruleApi } from '@/lib/api/outreach';
import type { OutreachRule, RuleType, ContentStrategy } from '@/types';

const { TextArea } = Input;
const { Title } = Typography;

const ruleTypeLabels: Record<RuleType, string> = {
  cart_abandoned: '购物车放弃',
  new_user_inactive: '新用户沉默',
  post_purchase: '购后触达',
  churn_risk: '流失风险',
  follow_up: '定时跟进',
};

const ruleTypeColors: Record<RuleType, string> = {
  cart_abandoned: 'orange',
  new_user_inactive: 'blue',
  post_purchase: 'green',
  churn_risk: 'red',
  follow_up: 'purple',
};

export default function RulesPage() {
  const [rules, setRules] = useState<OutreachRule[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [loading, setLoading] = useState(false);

  // 创建/编辑弹窗
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<OutreachRule | null>(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await ruleApi.list({ page, size });
      if (resp.success && resp.data) {
        setRules(resp.data.items);
        setTotal(resp.data.total);
      }
    } catch {
      message.error('加载规则列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, size]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const handleCreate = () => {
    setEditingRule(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (record: OutreachRule) => {
    setEditingRule(record);
    form.setFieldsValue({
      name: record.name,
      rule_type: record.rule_type,
      trigger_conditions: record.trigger_conditions ? JSON.stringify(record.trigger_conditions, null, 2) : '',
      content_strategy: record.content_strategy,
      content_template: record.content_template,
      ai_prompt: record.ai_prompt,
      max_triggers_per_user: record.max_triggers_per_user,
      cooldown_hours: record.cooldown_hours,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        name: values.name,
        rule_type: values.rule_type,
        trigger_conditions: values.trigger_conditions ? JSON.parse(values.trigger_conditions) : null,
        content_strategy: values.content_strategy,
        content_template: values.content_template || null,
        ai_prompt: values.ai_prompt || null,
        max_triggers_per_user: values.max_triggers_per_user,
        cooldown_hours: values.cooldown_hours,
      };

      setSubmitting(true);
      const resp = editingRule
        ? await ruleApi.update(editingRule.id, payload)
        : await ruleApi.create(payload);

      if (resp.success) {
        message.success(editingRule ? '更新成功' : '创建成功');
        setModalOpen(false);
        loadRules();
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
      const resp = await ruleApi.delete(id);
      if (resp.success) {
        message.success('删除成功');
        loadRules();
      }
    } catch {
      message.error('删除失败');
    }
  };

  const handleToggle = async (record: OutreachRule) => {
    try {
      const resp = await ruleApi.toggle(record.id);
      if (resp.success) {
        message.success(record.is_active ? '已禁用' : '已启用');
        loadRules();
      }
    } catch {
      message.error('操作失败');
    }
  };

  const columns: ColumnsType<OutreachRule> = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: '规则类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      width: 120,
      render: (type: RuleType) => (
        <Tag color={ruleTypeColors[type]}>
          {ruleTypeLabels[type]}
        </Tag>
      ),
    },
    {
      title: '内容策略',
      dataIndex: 'content_strategy',
      key: 'content_strategy',
      width: 120,
      render: (strategy: ContentStrategy) => (
        <Tag color={strategy === 'template' ? 'blue' : 'green'}>
          {strategy === 'template' ? '模板' : 'AI生成'}
        </Tag>
      ),
    },
    {
      title: '启用状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active: number, record) => (
        <Switch
          checked={!!active}
          onChange={() => handleToggle(record)}
        />
      ),
    },
    {
      title: '触发次数',
      dataIndex: 'total_triggered',
      key: 'total_triggered',
      width: 100,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: '转化次数',
      dataIndex: 'total_converted',
      key: 'total_converted',
      width: 100,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: '转化率',
      key: 'conversion_rate',
      width: 100,
      render: (_, record) => {
        const rate = record.total_triggered > 0
          ? ((record.total_converted / record.total_triggered) * 100).toFixed(2)
          : '0.00';
        return `${rate}%`;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description="删除后无法恢复，确认删除吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4} style={{ margin: 0 }}>
            <ThunderboltOutlined /> 自动规则管理
          </Title>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            创建规则
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={rules}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1200 }}
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
        title={editingRule ? '编辑规则' : '创建规则'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={submitting}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            content_strategy: 'template',
            max_triggers_per_user: 3,
            cooldown_hours: 24,
          }}
        >
          <Form.Item
            label="规则名称"
            name="name"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="请输入规则名称" />
          </Form.Item>

          <Form.Item
            label="规则类型"
            name="rule_type"
            rules={[{ required: true, message: '请选择规则类型' }]}
          >
            <Select placeholder="请选择规则类型">
              {Object.entries(ruleTypeLabels).map(([value, label]) => (
                <Select.Option key={value} value={value}>
                  {label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="触发条件 (JSON)"
            name="trigger_conditions"
            extra={'根据规则类型配置不同的触发条件，如: {"cart_idle_hours": 24, "min_cart_value": 100}'}
          >
            <TextArea
              rows={4}
              placeholder='{"cart_idle_hours": 24, "min_cart_value": 100}'
            />
          </Form.Item>

          <Form.Item
            label="内容策略"
            name="content_strategy"
            rules={[{ required: true, message: '请选择内容策略' }]}
          >
            <Select>
              <Select.Option value="template">模板</Select.Option>
              <Select.Option value="ai_generated">AI生成</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.content_strategy !== curr.content_strategy}
          >
            {({ getFieldValue }) =>
              getFieldValue('content_strategy') === 'template' ? (
                <Form.Item
                  label="内容模板"
                  name="content_template"
                  rules={[{ required: true, message: '请输入内容模板' }]}
                >
                  <TextArea
                    rows={4}
                    placeholder="您好，{user_name}，您的购物车还有商品未结算..."
                  />
                </Form.Item>
              ) : (
                <Form.Item
                  label="AI提示词"
                  name="ai_prompt"
                  rules={[{ required: true, message: '请输入AI提示词' }]}
                >
                  <TextArea
                    rows={4}
                    placeholder="根据用户的购物车商品，生成一条友好的提醒消息..."
                  />
                </Form.Item>
              )
            }
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="单用户最大触发次数"
                name="max_triggers_per_user"
                rules={[{ required: true, message: '请输入最大触发次数' }]}
              >
                <InputNumber
                  min={1}
                  max={100}
                  style={{ width: '100%' }}
                  placeholder="3"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="冷却时间 (小时)"
                name="cooldown_hours"
                rules={[{ required: true, message: '请输入冷却时间' }]}
              >
                <InputNumber
                  min={1}
                  max={720}
                  style={{ width: '100%' }}
                  placeholder="24"
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
}

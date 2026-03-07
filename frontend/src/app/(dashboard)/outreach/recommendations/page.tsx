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
  InputNumber,
  Popconfirm,
  Switch,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { recommendationApi } from '@/lib/api/outreach';
import type { RecommendationRule, RecommendationStats } from '@/types';

const { TextArea } = Input;

export default function RecommendationsPage() {
  const [loading, setLoading] = useState(false);
  const [rules, setRules] = useState<RecommendationRule[]>([]);
  const [stats, setStats] = useState<RecommendationStats | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<RecommendationRule | null>(null);
  const [form] = Form.useForm();

  const loadStats = useCallback(async () => {
    try {
      const resp = await recommendationApi.getStats();
      if (resp.success && resp.data) {
        setStats(resp.data);
      }
    } catch (err) {
      console.error('加载统计数据失败:', err);
    }
  }, []);

  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await recommendationApi.listRules({
        page,
        size: pageSize,
      });
      if (resp.success && resp.data) {
        setRules(resp.data.items);
        setTotal(resp.data.total);
      }
    } catch {
      message.error('加载推荐规则失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const handleCreate = async (values: Record<string, string>) => {
    try {
      // 处理数组字段
      const payload = {
        ...values,
        trigger_product_ids: values.trigger_product_ids
          ? values.trigger_product_ids.split(',').map((id: string) => parseInt(id.trim())).filter((id: number) => !isNaN(id))
          : null,
        recommend_product_ids: values.recommend_product_ids
          ? values.recommend_product_ids.split(',').map((id: string) => parseInt(id.trim())).filter((id: number) => !isNaN(id))
          : null,
      };

      const resp = editingRule
        ? await recommendationApi.updateRule(editingRule.id, payload)
        : await recommendationApi.createRule(payload);

      if (resp.success) {
        message.success(editingRule ? '更新成功' : '创建成功');
        setModalVisible(false);
        setEditingRule(null);
        form.resetFields();
        loadRules();
        loadStats();
      } else {
        message.error(resp.error?.message || '操作失败');
      }
    } catch {
      message.error('操作失败');
    }
  };

  const handleEdit = (rule: RecommendationRule) => {
    setEditingRule(rule);
    form.setFieldsValue({
      ...rule,
      trigger_product_ids: rule.trigger_product_ids?.join(', ') || '',
      recommend_product_ids: rule.recommend_product_ids?.join(', ') || '',
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      const resp = await recommendationApi.deleteRule(id);
      if (resp.success) {
        message.success('删除成功');
        loadRules();
        loadStats();
      } else {
        message.error(resp.error?.message || '删除失败');
      }
    } catch {
      message.error('删除失败');
    }
  };

  const typeLabels: Record<string, { text: string; color: string }> = {
    cross_sell: { text: '交叉销售', color: 'blue' },
    upsell: { text: '升级推荐', color: 'purple' },
    accessory: { text: '配件推荐', color: 'cyan' },
    consumable: { text: '耗材补充', color: 'orange' },
    replenish: { text: '复购提醒', color: 'green' },
  };

  const triggerTypeLabels: Record<string, string> = {
    in_conversation: '对话中',
    post_purchase: '购后',
    manual: '手动',
  };

  const strategyLabels: Record<string, string> = {
    manual: '手动配置',
    ai_similar: 'AI相似',
    ai_complementary: 'AI互补',
    popular_in_category: '分类热门',
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '推荐类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      render: (type: string) => {
        const label = typeLabels[type] || { text: type, color: 'default' };
        return <Tag color={label.color}>{label.text}</Tag>;
      },
    },
    {
      title: '触发类型',
      dataIndex: 'trigger_type',
      key: 'trigger_type',
      render: (type: string) => triggerTypeLabels[type] || type,
    },
    {
      title: '推荐策略',
      dataIndex: 'recommend_strategy',
      key: 'recommend_strategy',
      render: (strategy: string) => strategyLabels[strategy] || strategy,
    },
    {
      title: '启用状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: number) => (
        <Tag color={active ? 'success' : 'default'}>{active ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: RecommendationRule) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此推荐规则吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
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
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={4}>
          <Card>
            <Statistic
              title="总推荐"
              value={stats?.total_recommendations || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="总展示"
              value={stats?.total_displayed || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="总点击"
              value={stats?.total_clicked || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="总转化"
              value={stats?.total_converted || 0}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="点击率"
              value={stats?.click_rate || 0}
              precision={2}
              suffix="%"
              valueStyle={{ color: '#13c2c2' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="转化率"
              value={stats?.conversion_rate || 0}
              precision={2}
              suffix="%"
              valueStyle={{ color: '#eb2f96' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="推荐规则管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingRule(null);
              form.resetFields();
              setModalVisible(true);
            }}
          >
            创建规则
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={rules}
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
        title={editingRule ? '编辑推荐规则' : '创建推荐规则'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingRule(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            label="规则名称"
            name="name"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="请输入规则名称" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="推荐类型"
                name="rule_type"
                rules={[{ required: true, message: '请选择推荐类型' }]}
              >
                <Select placeholder="请选择推荐类型">
                  <Select.Option value="cross_sell">交叉销售</Select.Option>
                  <Select.Option value="upsell">升级推荐</Select.Option>
                  <Select.Option value="accessory">配件推荐</Select.Option>
                  <Select.Option value="consumable">耗材补充</Select.Option>
                  <Select.Option value="replenish">复购提醒</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="触发类型"
                name="trigger_type"
                rules={[{ required: true, message: '请选择触发类型' }]}
              >
                <Select placeholder="请选择触发类型">
                  <Select.Option value="in_conversation">对话中</Select.Option>
                  <Select.Option value="post_purchase">购后</Select.Option>
                  <Select.Option value="manual">手动</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="触发商品IDs" name="trigger_product_ids">
                <Input placeholder="多个ID用逗号分隔，如: 1, 2, 3" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="触发分类" name="trigger_category">
                <Input placeholder="请输入触发分类" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="推荐商品IDs" name="recommend_product_ids">
                <Input placeholder="多个ID用逗号分隔，如: 4, 5, 6" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="推荐分类" name="recommend_category">
                <Input placeholder="请输入推荐分类" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="推荐策略"
                name="recommend_strategy"
                rules={[{ required: true, message: '请选择推荐策略' }]}
              >
                <Select placeholder="请选择推荐策略">
                  <Select.Option value="manual">手动配置</Select.Option>
                  <Select.Option value="ai_similar">AI相似</Select.Option>
                  <Select.Option value="ai_complementary">AI互补</Select.Option>
                  <Select.Option value="popular_in_category">分类热门</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="最大推荐数"
                name="max_recommendations"
                rules={[{ required: true, message: '请输入最大推荐数' }]}
                initialValue={3}
              >
                <InputNumber style={{ width: '100%' }} placeholder="请输入最大推荐数" min={1} max={10} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="AI提示词" name="ai_prompt">
            <TextArea
              rows={3}
              placeholder="当使用AI策略时的提示词"
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="优先级"
                name="priority"
                rules={[{ required: true, message: '请输入优先级' }]}
                initialValue={0}
              >
                <InputNumber style={{ width: '100%' }} placeholder="数字越大优先级越高" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="启用状态"
                name="is_active"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
}

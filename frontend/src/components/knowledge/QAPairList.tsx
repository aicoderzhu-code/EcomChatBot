'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Table, Button, Input, Select, Tag, Space, Modal, Form,
  message, Popconfirm, Upload, Card, Tooltip,
} from 'antd';
import {
  PlusOutlined, SearchOutlined, UploadOutlined,
  SyncOutlined, FireOutlined, DeleteOutlined, EditOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { qaApi, QAPair } from '@/lib/api/qa';

const { TextArea } = Input;

export default function QAPairList() {
  const [qaList, setQaList] = useState<QAPair[]>([]);
  const [loading, setLoading] = useState(true);
  const [keyword, setKeyword] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  // Editor modal
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingQa, setEditingQa] = useState<QAPair | null>(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  // Import modal
  const [importOpen, setImportOpen] = useState(false);

  const loadData = useCallback(async (page: number, pageSize: number) => {
    setLoading(true);
    try {
      const resp = await qaApi.list({
        keyword: keyword || undefined,
        category: categoryFilter || undefined,
        page,
        size: pageSize,
      });
      if (resp.success && resp.data) {
        setQaList(resp.data.items);
        setPagination(prev => ({ ...prev, total: resp.data!.total }));
      }
    } catch {
      message.error('加载 QA 对失败');
    } finally {
      setLoading(false);
    }
  }, [keyword, categoryFilter]);

  useEffect(() => {
    loadData(pagination.current, pagination.pageSize);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadData, pagination.current, pagination.pageSize]);

  const handleCreate = () => {
    setEditingQa(null);
    form.resetFields();
    setEditorOpen(true);
  };

  const handleEdit = (record: QAPair) => {
    setEditingQa(record);
    form.setFieldsValue({
      question: record.question,
      answer: record.answer,
      category: record.category,
      priority: record.priority,
    });
    setEditorOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      if (editingQa) {
        await qaApi.update(editingQa.qa_id, values);
        message.success('更新成功');
      } else {
        await qaApi.create(values);
        message.success('创建成功');
      }
      setEditorOpen(false);
      loadData(pagination.current, pagination.pageSize);
    } catch {
      // form validation error
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (qaId: string) => {
    try {
      await qaApi.delete(qaId);
      message.success('删除成功');
      loadData(pagination.current, pagination.pageSize);
    } catch {
      message.error('删除失败');
    }
  };

  const handleRegenerateVariations = async (qaId: string) => {
    try {
      message.loading({ content: '正在生成变体...', key: 'regen' });
      await qaApi.regenerateVariations(qaId);
      message.success({ content: '变体生成完成', key: 'regen' });
      loadData(pagination.current, pagination.pageSize);
    } catch {
      message.error({ content: '变体生成失败', key: 'regen' });
    }
  };

  const handleImport = async (file: File) => {
    try {
      const resp = await qaApi.importCsv(file);
      if (resp.success && resp.data) {
        message.success(`导入成功 ${resp.data.success_count} 条，失败 ${resp.data.failed_count} 条`);
        setImportOpen(false);
        loadData(1, pagination.pageSize);
      }
    } catch {
      message.error('导入失败');
    }
  };

  const columns: ColumnsType<QAPair> = [
    {
      title: '问题',
      dataIndex: 'question',
      width: 300,
      ellipsis: true,
    },
    {
      title: '答案',
      dataIndex: 'answer',
      width: 300,
      ellipsis: true,
    },
    {
      title: '变体数',
      dataIndex: 'variations',
      width: 80,
      render: (v: string[] | null) => v?.length || 0,
    },
    {
      title: '分类',
      dataIndex: 'category',
      width: 100,
      render: (v: string | null) => v ? <Tag>{v}</Tag> : '-',
    },
    {
      title: '使用次数',
      dataIndex: 'use_count',
      width: 90,
      sorter: (a, b) => a.use_count - b.use_count,
      render: (v: number) => v > 0 ? <span><FireOutlined style={{ color: '#f5222d' }} /> {v}</span> : v,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (v: string) => (
        <Tag color={v === 'active' ? 'green' : 'default'}>
          {v === 'active' ? '启用' : '停用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Tooltip title="重新生成变体">
            <Button size="small" icon={<SyncOutlined />} onClick={() => handleRegenerateVariations(record.qa_id)} />
          </Tooltip>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.qa_id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="问答对管理"
      extra={
        <Space>
          <Button icon={<UploadOutlined />} onClick={() => setImportOpen(true)}>
            CSV 导入
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建 QA 对
          </Button>
        </Space>
      }
    >
      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="搜索问题或答案"
          prefix={<SearchOutlined />}
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          style={{ width: 250 }}
          allowClear
        />
        <Select
          placeholder="分类筛选"
          value={categoryFilter || undefined}
          onChange={v => setCategoryFilter(v || '')}
          style={{ width: 150 }}
          allowClear
          options={[
            { label: '全部', value: '' },
            { label: '售后', value: '售后' },
            { label: '物流', value: '物流' },
            { label: '商品', value: '商品' },
            { label: '支付', value: '支付' },
          ]}
        />
      </Space>

      <Table
        columns={columns}
        dataSource={qaList}
        rowKey="qa_id"
        loading={loading}
        pagination={{
          ...pagination,
          showSizeChanger: true,
          showTotal: total => `共 ${total} 条`,
          onChange: (page, pageSize) => setPagination(prev => ({ ...prev, current: page, pageSize })),
        }}
      />

      {/* QA 编辑弹窗 */}
      <Modal
        title={editingQa ? '编辑 QA 对' : '新建 QA 对'}
        open={editorOpen}
        onOk={handleSave}
        onCancel={() => setEditorOpen(false)}
        confirmLoading={saving}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="question" label="问题" rules={[{ required: true, message: '请输入问题' }]}>
            <TextArea rows={2} placeholder="输入标准问题" />
          </Form.Item>
          <Form.Item name="answer" label="答案" rules={[{ required: true, message: '请输入答案' }]}>
            <TextArea rows={4} placeholder="输入标准答案" />
          </Form.Item>
          <Form.Item name="category" label="分类">
            <Input placeholder="如：售后、物流、商品" />
          </Form.Item>
          <Form.Item name="priority" label="优先级" initialValue={0}>
            <Input type="number" min={0} />
          </Form.Item>
        </Form>
      </Modal>

      {/* CSV 导入弹窗 */}
      <Modal
        title="CSV 批量导入"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        footer={null}
      >
        <p style={{ marginBottom: 16 }}>CSV 格式：question,answer,category（第一行为表头）</p>
        <Upload.Dragger
          accept=".csv"
          showUploadList={false}
          beforeUpload={(file) => {
            handleImport(file);
            return false;
          }}
        >
          <p className="ant-upload-text">点击或拖拽 CSV 文件到此处</p>
        </Upload.Dragger>
      </Modal>
    </Card>
  );
}

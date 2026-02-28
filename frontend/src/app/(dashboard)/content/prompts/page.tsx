'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Button, Input, Select, Space, Tag, Table, message,
  Typography, Modal, Popconfirm,
} from 'antd';
import { FormOutlined, PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { contentApi, type ProductPrompt } from '@/lib/api/content';
import { productApi } from '@/lib/api/product';
import type { Product } from '@/types';

const { TextArea } = Input;
const { Title, Text } = Typography;

const PROMPT_TYPE_OPTIONS = [
  { value: 'image', label: '图片', color: 'blue' },
  { value: 'video', label: '视频', color: 'purple' },
  { value: 'title', label: '标题', color: 'green' },
  { value: 'description', label: '描述', color: 'orange' },
];

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<ProductPrompt[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filterProductId, setFilterProductId] = useState<number | undefined>();
  const [filterType, setFilterType] = useState<string | undefined>();

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState<ProductPrompt | null>(null);
  const [formProductId, setFormProductId] = useState<number | undefined>();
  const [formType, setFormType] = useState<string | undefined>();
  const [formName, setFormName] = useState('');
  const [formContent, setFormContent] = useState('');
  const [saving, setSaving] = useState(false);

  const loadProducts = useCallback(async () => {
    try {
      const resp = await productApi.listProducts({ status: 'active', size: 200 });
      if (resp.success && resp.data) setProducts(resp.data.items);
    } catch { /* ignore */ }
  }, []);

  const loadPrompts = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await contentApi.listPrompts({
        product_id: filterProductId,
        prompt_type: filterType,
        page,
        size: 20,
      });
      if (resp.success && resp.data) {
        setPrompts(resp.data.items);
        setTotal(resp.data.total);
      }
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [filterProductId, filterType, page]);

  useEffect(() => { loadProducts(); }, [loadProducts]);
  useEffect(() => { loadPrompts(); }, [loadPrompts]);

  const openCreateModal = () => {
    setEditingPrompt(null);
    setFormProductId(filterProductId);
    setFormType(filterType);
    setFormName('');
    setFormContent('');
    setModalOpen(true);
  };

  const openEditModal = (prompt: ProductPrompt) => {
    setEditingPrompt(prompt);
    setFormProductId(prompt.product_id);
    setFormType(prompt.prompt_type);
    setFormName(prompt.name);
    setFormContent(prompt.content);
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!formName.trim() || !formContent.trim()) {
      message.warning('请填写名称和内容');
      return;
    }
    setSaving(true);
    try {
      if (editingPrompt) {
        const resp = await contentApi.updatePrompt(editingPrompt.id, {
          name: formName.trim(),
          content: formContent.trim(),
        });
        if (resp.success) {
          message.success('更新成功');
          setModalOpen(false);
          loadPrompts();
        } else {
          message.error(resp.error?.message || '更新失败');
        }
      } else {
        if (!formProductId || !formType) {
          message.warning('请选择商品和类型');
          setSaving(false);
          return;
        }
        const resp = await contentApi.createPrompt({
          product_id: formProductId,
          prompt_type: formType,
          name: formName.trim(),
          content: formContent.trim(),
        });
        if (resp.success) {
          message.success('创建成功');
          setModalOpen(false);
          loadPrompts();
        } else {
          message.error(resp.error?.message || '创建失败');
        }
      }
    } catch {
      message.error('操作失败');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      const resp = await contentApi.deletePrompt(id);
      if (resp.success) {
        message.success('已删除');
        loadPrompts();
      }
    } catch {
      message.error('删除失败');
    }
  };

  const getProductName = (productId: number) => {
    const p = products.find(p => p.id === productId);
    return p?.title || `商品#${productId}`;
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 180,
    },
    {
      title: '类型',
      dataIndex: 'prompt_type',
      key: 'prompt_type',
      width: 80,
      render: (type: string) => {
        const opt = PROMPT_TYPE_OPTIONS.find(o => o.value === type);
        return <Tag color={opt?.color}>{opt?.label || type}</Tag>;
      },
    },
    {
      title: '关联商品',
      dataIndex: 'product_id',
      key: 'product_id',
      width: 180,
      render: (id: number) => <Text ellipsis style={{ maxWidth: 160 }}>{getProductName(id)}</Text>,
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
    },
    {
      title: '使用次数',
      dataIndex: 'usage_count',
      key: 'usage_count',
      width: 90,
      align: 'center' as const,
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: ProductPrompt) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEditModal(record)}
          />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        <FormOutlined style={{ marginRight: 8 }} />
        提示词管理
      </Title>

      <Card>
        <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Select
              placeholder="筛选商品"
              allowClear
              style={{ width: 200 }}
              value={filterProductId}
              onChange={(v) => { setFilterProductId(v); setPage(1); }}
              showSearch
              optionFilterProp="label"
              options={products.map(p => ({ value: p.id, label: p.title }))}
            />
            <Select
              placeholder="筛选类型"
              allowClear
              style={{ width: 120 }}
              value={filterType}
              onChange={(v) => { setFilterType(v); setPage(1); }}
              options={PROMPT_TYPE_OPTIONS}
            />
          </Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            新增提示词
          </Button>
        </Space>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={prompts}
          loading={loading}
          pagination={{
            current: page,
            total,
            pageSize: 20,
            onChange: setPage,
            showTotal: (t) => `共 ${t} 条`,
          }}
        />
      </Card>

      <Modal
        title={editingPrompt ? '编辑提示词' : '新增提示词'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        confirmLoading={saving}
        okText={editingPrompt ? '保存' : '创建'}
        width={600}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {!editingPrompt && (
            <>
              <div>
                <Text strong>商品</Text>
                <Select
                  placeholder="选择商品"
                  style={{ width: '100%', marginTop: 4 }}
                  value={formProductId}
                  onChange={setFormProductId}
                  showSearch
                  optionFilterProp="label"
                  options={products.map(p => ({ value: p.id, label: p.title }))}
                />
              </div>
              <div>
                <Text strong>类型</Text>
                <Select
                  placeholder="选择类型"
                  style={{ width: '100%', marginTop: 4 }}
                  value={formType}
                  onChange={setFormType}
                  options={PROMPT_TYPE_OPTIONS}
                />
              </div>
            </>
          )}
          <div>
            <Text strong>名称</Text>
            <Input
              placeholder="提示词名称"
              value={formName}
              onChange={e => setFormName(e.target.value)}
              style={{ marginTop: 4 }}
            />
          </div>
          <div>
            <Text strong>内容</Text>
            <TextArea
              rows={6}
              placeholder="提示词内容"
              value={formContent}
              onChange={e => setFormContent(e.target.value)}
              style={{ marginTop: 4 }}
            />
          </div>
        </Space>
      </Modal>
    </div>
  );
}

'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Input, Select, Space, Tag, Image,
  message, Modal, Typography, Descriptions, Progress, Tooltip,
  InputNumber, Switch, Row, Col, Statistic,
} from 'antd';
import {
  SyncOutlined, ShoppingOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { productApi } from '@/lib/api/product';
import type { Product, SyncTask, SyncSchedule } from '@/types';

const { Search } = Input;
const { Text, Title } = Typography;

export default function ProductsPage() {
  // 商品列表状态
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);

  // 同步状态
  const [syncTasks, setSyncTasks] = useState<SyncTask[]>([]);
  const [syncSchedule, setSyncSchedule] = useState<SyncSchedule | null>(null);
  const [syncing, setSyncing] = useState(false);

  // 商品详情弹窗
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // 同步配置弹窗
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [scheduleInterval, setScheduleInterval] = useState(60);
  const [scheduleActive, setScheduleActive] = useState(true);

  const loadProducts = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await productApi.listProducts({
        keyword: keyword || undefined,
        status: statusFilter,
        page,
        size,
      });
      if (resp.success && resp.data) {
        setProducts(resp.data.items);
        setTotal(resp.data.total);
      }
    } catch {
      message.error('加载商品列表失败');
    } finally {
      setLoading(false);
    }
  }, [keyword, statusFilter, page, size]);

  const loadSyncTasks = useCallback(async () => {
    try {
      const resp = await productApi.listSyncTasks({ page: 1, size: 5 });
      if (resp.success && resp.data) {
        setSyncTasks(resp.data.items);
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  useEffect(() => {
    loadSyncTasks();
  }, [loadSyncTasks]);

  const handleSync = async (syncType: 'full' | 'incremental') => {
    setSyncing(true);
    try {
      // TODO: 支持多平台选择，当前使用第一个平台
      const resp = await productApi.triggerSync(1, syncType);
      if (resp.success) {
        message.success('同步任务已创建');
        loadSyncTasks();
      } else {
        message.error(resp.error?.message || '触发同步失败');
      }
    } catch {
      message.error('触发同步失败');
    } finally {
      setSyncing(false);
    }
  };

  const handleSaveSchedule = async () => {
    try {
      // TODO: 支持多平台选择
      const resp = await productApi.updateSyncSchedule(1, {
        interval_minutes: scheduleInterval,
        is_active: scheduleActive,
      });
      if (resp.success) {
        message.success('同步配置已更新');
        setSyncSchedule(resp.data);
        setScheduleOpen(false);
      }
    } catch {
      message.error('更新同步配置失败');
    }
  };

  const statusTagMap: Record<string, { color: string; text: string }> = {
    active: { color: 'green', text: '在售' },
    inactive: { color: 'default', text: '下架' },
    deleted: { color: 'red', text: '已删除' },
  };

  const columns: ColumnsType<Product> = [
    {
      title: '商品图片',
      dataIndex: 'images',
      width: 80,
      render: (images: string[] | null) =>
        images && images.length > 0 ? (
          <Image src={images[0]} alt="商品图片" width={60} height={60} style={{ objectFit: 'cover', borderRadius: 4 }} />
        ) : (
          <div style={{ width: 60, height: 60, background: '#f0f0f0', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ShoppingOutlined style={{ fontSize: 20, color: '#999' }} />
          </div>
        ),
    },
    {
      title: '商品标题',
      dataIndex: 'title',
      ellipsis: true,
      render: (title: string, record) => (
        <a onClick={() => { setSelectedProduct(record); setDetailOpen(true); }}>{title}</a>
      ),
    },
    {
      title: '价格',
      dataIndex: 'price',
      width: 120,
      render: (price: number, record) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ color: '#f5222d' }}>&yen;{price.toFixed(2)}</Text>
          {record.original_price && (
            <Text delete type="secondary" style={{ fontSize: 12 }}>&yen;{record.original_price.toFixed(2)}</Text>
          )}
        </Space>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      width: 100,
      render: (cat: string | null) => cat || '-',
    },
    {
      title: '销量',
      dataIndex: 'sales_count',
      width: 80,
      sorter: (a, b) => a.sales_count - b.sales_count,
    },
    {
      title: '库存',
      dataIndex: 'stock',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (status: string) => {
        const tag = statusTagMap[status] || { color: 'default', text: status };
        return <Tag color={tag.color}>{tag.text}</Tag>;
      },
    },
    {
      title: '最近同步',
      dataIndex: 'last_synced_at',
      width: 160,
      render: (time: string | null) =>
        time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        <ShoppingOutlined style={{ marginRight: 8 }} />
        商品管理
      </Title>

      {/* 同步状态卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="商品总数" value={total} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="在售商品"
              value={products.filter(p => p.status === 'active').length}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="最近同步"
              value={
                syncTasks.length > 0 && syncTasks[0].completed_at
                  ? new Date(syncTasks[0].completed_at).toLocaleString('zh-CN')
                  : '暂无'
              }
              valueStyle={{ fontSize: 14 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Space>
              <Button
                type="primary"
                icon={<SyncOutlined spin={syncing} />}
                loading={syncing}
                onClick={() => handleSync('full')}
              >
                全量同步
              </Button>
              <Button
                icon={<SyncOutlined />}
                onClick={() => handleSync('incremental')}
              >
                增量同步
              </Button>
              <Tooltip title="同步调度配置">
                <Button
                  icon={<ClockCircleOutlined />}
                  onClick={() => setScheduleOpen(true)}
                />
              </Tooltip>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 最近同步任务 */}
      {syncTasks.length > 0 && syncTasks[0].status === 'running' && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Space>
            <LoadingOutlined />
            <Text>正在同步中...</Text>
            <Progress
              percent={
                syncTasks[0].total_count > 0
                  ? Math.round((syncTasks[0].synced_count / syncTasks[0].total_count) * 100)
                  : 0
              }
              size="small"
              style={{ width: 200 }}
            />
            <Text type="secondary">
              {syncTasks[0].synced_count}/{syncTasks[0].total_count}
            </Text>
          </Space>
        </Card>
      )}

      {/* 搜索和筛选 */}
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Search
            placeholder="搜索商品标题"
            allowClear
            style={{ width: 300 }}
            onSearch={(value) => { setKeyword(value); setPage(1); }}
          />
          <Select
            placeholder="商品状态"
            allowClear
            style={{ width: 120 }}
            value={statusFilter}
            onChange={(value) => { setStatusFilter(value); setPage(1); }}
            options={[
              { value: 'active', label: '在售' },
              { value: 'inactive', label: '下架' },
              { value: 'deleted', label: '已删除' },
            ]}
          />
        </Space>
      </Card>

      {/* 商品表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={products}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: size,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 件商品`,
            onChange: (p, s) => { setPage(p); setSize(s); },
          }}
        />
      </Card>

      {/* 商品详情弹窗 */}
      <Modal
        title="商品详情"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={700}
      >
        {selectedProduct && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="商品标题" span={2}>{selectedProduct.title}</Descriptions.Item>
            <Descriptions.Item label="价格">&yen;{selectedProduct.price}</Descriptions.Item>
            <Descriptions.Item label="原价">
              {selectedProduct.original_price ? `¥${selectedProduct.original_price}` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="分类">{selectedProduct.category || '-'}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={statusTagMap[selectedProduct.status]?.color}>
                {statusTagMap[selectedProduct.status]?.text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="销量">{selectedProduct.sales_count}</Descriptions.Item>
            <Descriptions.Item label="库存">{selectedProduct.stock}</Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>
              {selectedProduct.description || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="商品图片" span={2}>
              <Space>
                {selectedProduct.images?.map((img, idx) => (
                  <Image key={idx} src={img} alt={`商品图片${idx + 1}`} width={80} height={80} style={{ objectFit: 'cover' }} />
                ))}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="知识库关联">
              {selectedProduct.knowledge_base_id ? (
                <Tag color="blue">已关联 (ID: {selectedProduct.knowledge_base_id})</Tag>
              ) : (
                <Tag>未关联</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="最近同步">
              {selectedProduct.last_synced_at
                ? new Date(selectedProduct.last_synced_at).toLocaleString('zh-CN')
                : '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* 同步调度配置弹窗 */}
      <Modal
        title="同步调度配置"
        open={scheduleOpen}
        onCancel={() => setScheduleOpen(false)}
        onOk={handleSaveSchedule}
        okText="保存"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Text>启用定时同步</Text>
            <Switch
              checked={scheduleActive}
              onChange={setScheduleActive}
              style={{ marginLeft: 16 }}
            />
          </div>
          <div>
            <Text>同步间隔（分钟）</Text>
            <InputNumber
              min={10}
              max={1440}
              value={scheduleInterval}
              onChange={(v) => v && setScheduleInterval(v)}
              style={{ marginLeft: 16, width: 120 }}
            />
          </div>
          {syncSchedule && (
            <div>
              <Text type="secondary">
                上次同步：{syncSchedule.last_run_at ? new Date(syncSchedule.last_run_at).toLocaleString('zh-CN') : '暂无'}
              </Text>
              <br />
              <Text type="secondary">
                下次同步：{syncSchedule.next_run_at ? new Date(syncSchedule.next_run_at).toLocaleString('zh-CN') : '暂无'}
              </Text>
            </div>
          )}
        </Space>
      </Modal>
    </div>
  );
}

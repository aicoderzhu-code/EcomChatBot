'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Input, InputNumber, Select, Space, Tag,
  message, Modal, Form, Typography, Descriptions, Row, Col,
  Statistic, Popconfirm, Spin,
} from 'antd';
import {
  DollarOutlined, PlusOutlined, DeleteOutlined,
  ThunderboltOutlined, HistoryOutlined, ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { pricingApi } from '@/lib/api/pricing';
import { productApi } from '@/lib/api/product';
import type { CompetitorProduct, PricingAnalysis } from '@/lib/api/pricing';
import type { Product } from '@/types';

const { Text, Title, Paragraph } = Typography;

const strategyLabels: Record<string, { label: string; color: string }> = {
  competitive: { label: '竞争定价', color: 'blue' },
  premium: { label: '高端定价', color: 'purple' },
  penetration: { label: '渗透定价', color: 'green' },
  dynamic: { label: '动态定价', color: 'orange' },
};

export default function PricingPage() {
  // 商品选择
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<number | undefined>();
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [loadingProducts, setLoadingProducts] = useState(false);

  // 竞品列表
  const [competitors, setCompetitors] = useState<CompetitorProduct[]>([]);
  const [competitorTotal, setCompetitorTotal] = useState(0);
  const [competitorPage, setCompetitorPage] = useState(1);
  const [loadingCompetitors, setLoadingCompetitors] = useState(false);

  // 添加竞品弹窗
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [addForm] = Form.useForm();
  const [adding, setAdding] = useState(false);

  // 定价分析
  const [latestAnalysis, setLatestAnalysis] = useState<PricingAnalysis | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [strategy, setStrategy] = useState('competitive');

  // 分析历史
  const [historyOpen, setHistoryOpen] = useState(false);
  const [analysisHistory, setAnalysisHistory] = useState<PricingAnalysis[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // 加载商品列表
  const loadProducts = useCallback(async () => {
    setLoadingProducts(true);
    try {
      const resp = await productApi.listProducts({ status: 'active', size: 100 });
      if (resp.success && resp.data) {
        setProducts(resp.data.items);
      }
    } catch {
      message.error('加载商品列表失败');
    } finally {
      setLoadingProducts(false);
    }
  }, []);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  // 加载竞品列表
  const loadCompetitors = useCallback(async () => {
    if (!selectedProductId) return;
    setLoadingCompetitors(true);
    try {
      const resp = await pricingApi.listCompetitors(selectedProductId, {
        page: competitorPage,
        size: 20,
      });
      if (resp.success && resp.data) {
        setCompetitors(resp.data.items);
        setCompetitorTotal(resp.data.total);
      }
    } catch {
      message.error('加载竞品数据失败');
    } finally {
      setLoadingCompetitors(false);
    }
  }, [selectedProductId, competitorPage]);

  // 加载最新分析
  const loadLatestAnalysis = useCallback(async () => {
    if (!selectedProductId) return;
    try {
      const resp = await pricingApi.getLatestAnalysis(selectedProductId);
      if (resp.success && resp.data) {
        setLatestAnalysis(resp.data);
      } else {
        setLatestAnalysis(null);
      }
    } catch {
      setLatestAnalysis(null);
    }
  }, [selectedProductId]);

  useEffect(() => {
    if (selectedProductId) {
      const product = products.find((p) => p.id === selectedProductId) || null;
      setSelectedProduct(product);
      loadCompetitors();
      loadLatestAnalysis();
    } else {
      setSelectedProduct(null);
      setCompetitors([]);
      setLatestAnalysis(null);
    }
  }, [selectedProductId, products, loadCompetitors, loadLatestAnalysis]);

  // 添加竞品
  const handleAddCompetitor = async () => {
    if (!selectedProductId) return;
    try {
      const values = await addForm.validateFields();
      setAdding(true);
      const resp = await pricingApi.addCompetitor({
        product_id: selectedProductId,
        ...values,
      });
      if (resp.success) {
        message.success('竞品已添加');
        setAddModalOpen(false);
        addForm.resetFields();
        loadCompetitors();
      } else {
        message.error(resp.error?.message || '添加失败');
      }
    } catch {
      // form validation error
    } finally {
      setAdding(false);
    }
  };

  // 删除竞品
  const handleDeleteCompetitor = async (competitorId: number) => {
    try {
      const resp = await pricingApi.deleteCompetitor(competitorId);
      if (resp.success) {
        message.success('已删除');
        loadCompetitors();
      } else {
        message.error(resp.error?.message || '删除失败');
      }
    } catch {
      message.error('删除失败');
    }
  };

  // 执行定价分析
  const handleAnalyze = async () => {
    if (!selectedProductId) return;
    setAnalyzing(true);
    try {
      const resp = await pricingApi.analyzePricing({
        product_id: selectedProductId,
        strategy,
      });
      if (resp.success && resp.data) {
        setLatestAnalysis(resp.data);
        message.success('定价分析完成');
      } else {
        message.error(resp.error?.message || '分析失败');
      }
    } catch {
      message.error('定价分析失败');
    } finally {
      setAnalyzing(false);
    }
  };

  // 加载分析历史
  const loadHistory = useCallback(async () => {
    if (!selectedProductId) return;
    setLoadingHistory(true);
    try {
      const resp = await pricingApi.listAnalysisHistory(selectedProductId, {
        page: historyPage,
        size: 10,
      });
      if (resp.success && resp.data) {
        setAnalysisHistory(resp.data.items);
        setHistoryTotal(resp.data.total);
      }
    } catch {
      message.error('加载分析历史失败');
    } finally {
      setLoadingHistory(false);
    }
  }, [selectedProductId, historyPage]);

  useEffect(() => {
    if (historyOpen) {
      loadHistory();
    }
  }, [historyOpen, loadHistory]);

  // 竞品表格列
  const competitorColumns: ColumnsType<CompetitorProduct> = [
    {
      title: '竞品名称',
      dataIndex: 'competitor_name',
      ellipsis: true,
    },
    {
      title: '平台',
      dataIndex: 'competitor_platform',
      width: 100,
      render: (v: string | null) => v || '-',
    },
    {
      title: '价格',
      dataIndex: 'competitor_price',
      width: 120,
      render: (price: number) => (
        <Text strong style={{ color: '#f5222d' }}>
          &yen;{Number(price).toFixed(2)}
        </Text>
      ),
    },
    {
      title: '销量',
      dataIndex: 'competitor_sales',
      width: 80,
    },
    {
      title: '链接',
      dataIndex: 'competitor_url',
      width: 80,
      render: (url: string | null) =>
        url ? (
          <a href={url} target="_blank" rel="noopener noreferrer">
            查看
          </a>
        ) : (
          '-'
        ),
    },
    {
      title: '操作',
      width: 80,
      render: (_, record) => (
        <Popconfirm
          title="确定要删除此竞品数据吗？"
          onConfirm={() => handleDeleteCompetitor(record.id)}
        >
          <Button type="link" danger icon={<DeleteOutlined />} size="small">
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  // 分析历史列
  const historyColumns: ColumnsType<PricingAnalysis> = [
    {
      title: '分析时间',
      dataIndex: 'created_at',
      width: 180,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '当前价格',
      dataIndex: 'current_price',
      width: 100,
      render: (v: number) => `¥${Number(v).toFixed(2)}`,
    },
    {
      title: '建议价格',
      dataIndex: 'suggested_price',
      width: 100,
      render: (v: number) => (
        <Text strong style={{ color: '#1890ff' }}>
          ¥{Number(v).toFixed(2)}
        </Text>
      ),
    },
    {
      title: '策略',
      dataIndex: 'strategy',
      width: 100,
      render: (v: string) => {
        const s = strategyLabels[v] || { label: v, color: 'default' };
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
    {
      title: '竞品数',
      dataIndex: 'competitor_count',
      width: 80,
    },
    {
      title: '摘要',
      dataIndex: 'analysis_summary',
      ellipsis: true,
      render: (v: string | null) => v || '-',
    },
  ];

  // 价格变化百分比
  const priceDiffPercent =
    latestAnalysis && latestAnalysis.current_price > 0
      ? (
          ((latestAnalysis.suggested_price - latestAnalysis.current_price) /
            latestAnalysis.current_price) *
          100
        ).toFixed(1)
      : null;

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        <DollarOutlined style={{ marginRight: 8 }} />
        智能定价
      </Title>

      {/* 商品选择器 */}
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Text strong>选择商品：</Text>
          <Select
            placeholder="请选择一个商品"
            style={{ width: 400 }}
            loading={loadingProducts}
            showSearch
            optionFilterProp="label"
            value={selectedProductId}
            onChange={(v) => {
              setSelectedProductId(v);
              setCompetitorPage(1);
            }}
            options={products.map((p) => ({
              value: p.id,
              label: `${p.title} (¥${Number(p.price).toFixed(2)})`,
            }))}
            allowClear
          />
          {selectedProduct && (
            <Space>
              <Tag color="blue">¥{Number(selectedProduct.price).toFixed(2)}</Tag>
              <Tag>销量 {selectedProduct.sales_count}</Tag>
              <Tag>库存 {selectedProduct.stock}</Tag>
            </Space>
          )}
        </Space>
      </Card>

      {selectedProductId && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            {/* 竞品数据 */}
            <Col span={14}>
              <Card
                title="竞品数据"
                extra={
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => setAddModalOpen(true)}
                  >
                    添加竞品
                  </Button>
                }
              >
                <Table
                  columns={competitorColumns}
                  dataSource={competitors}
                  rowKey="id"
                  loading={loadingCompetitors}
                  size="small"
                  pagination={{
                    current: competitorPage,
                    pageSize: 20,
                    total: competitorTotal,
                    showTotal: (t) => `共 ${t} 条`,
                    onChange: (p) => setCompetitorPage(p),
                    size: 'small',
                  }}
                />
              </Card>
            </Col>

            {/* 定价分析 */}
            <Col span={10}>
              <Card
                title="定价分析"
                extra={
                  <Space>
                    <Button
                      icon={<HistoryOutlined />}
                      onClick={() => setHistoryOpen(true)}
                    >
                      历史
                    </Button>
                  </Space>
                }
              >
                <Space
                  direction="vertical"
                  style={{ width: '100%' }}
                  size="middle"
                >
                  <Space>
                    <Text>定价策略：</Text>
                    <Select
                      value={strategy}
                      onChange={setStrategy}
                      style={{ width: 140 }}
                      options={Object.entries(strategyLabels).map(
                        ([k, v]) => ({
                          value: k,
                          label: v.label,
                        })
                      )}
                    />
                    <Button
                      type="primary"
                      icon={<ThunderboltOutlined />}
                      loading={analyzing}
                      onClick={handleAnalyze}
                    >
                      开始分析
                    </Button>
                  </Space>

                  {analyzing && (
                    <div style={{ textAlign: 'center', padding: '20px 0' }}>
                      <Spin tip="正在分析定价..." />
                    </div>
                  )}

                  {latestAnalysis && !analyzing && (
                    <>
                      <Row gutter={16}>
                        <Col span={12}>
                          <Statistic
                            title="当前价格"
                            value={Number(latestAnalysis.current_price)}
                            precision={2}
                            prefix="¥"
                          />
                        </Col>
                        <Col span={12}>
                          <Statistic
                            title="建议价格"
                            value={Number(latestAnalysis.suggested_price)}
                            precision={2}
                            prefix="¥"
                            valueStyle={{
                              color:
                                latestAnalysis.suggested_price >
                                latestAnalysis.current_price
                                  ? '#cf1322'
                                  : '#3f8600',
                            }}
                            suffix={
                              priceDiffPercent && (
                                <Text
                                  style={{
                                    fontSize: 14,
                                    color:
                                      Number(priceDiffPercent) > 0
                                        ? '#cf1322'
                                        : '#3f8600',
                                  }}
                                >
                                  {Number(priceDiffPercent) > 0 ? (
                                    <ArrowUpOutlined />
                                  ) : (
                                    <ArrowDownOutlined />
                                  )}
                                  {Math.abs(Number(priceDiffPercent))}%
                                </Text>
                              )
                            }
                          />
                        </Col>
                      </Row>

                      <Descriptions
                        size="small"
                        column={2}
                        bordered
                        style={{ marginTop: 12 }}
                      >
                        <Descriptions.Item label="建议最低价">
                          {latestAnalysis.min_price
                            ? `¥${Number(latestAnalysis.min_price).toFixed(2)}`
                            : '-'}
                        </Descriptions.Item>
                        <Descriptions.Item label="建议最高价">
                          {latestAnalysis.max_price
                            ? `¥${Number(latestAnalysis.max_price).toFixed(2)}`
                            : '-'}
                        </Descriptions.Item>
                        <Descriptions.Item label="竞品均价">
                          {latestAnalysis.competitor_avg_price
                            ? `¥${Number(latestAnalysis.competitor_avg_price).toFixed(2)}`
                            : '-'}
                        </Descriptions.Item>
                        <Descriptions.Item label="参考竞品数">
                          {latestAnalysis.competitor_count}
                        </Descriptions.Item>
                        <Descriptions.Item label="定价策略" span={2}>
                          <Tag
                            color={
                              strategyLabels[latestAnalysis.strategy]?.color ||
                              'default'
                            }
                          >
                            {strategyLabels[latestAnalysis.strategy]?.label ||
                              latestAnalysis.strategy}
                          </Tag>
                        </Descriptions.Item>
                      </Descriptions>

                      {latestAnalysis.analysis_summary && (
                        <Card
                          size="small"
                          title="AI 分析摘要"
                          style={{ marginTop: 12 }}
                        >
                          <Paragraph style={{ marginBottom: 0 }}>
                            {latestAnalysis.analysis_summary}
                          </Paragraph>
                        </Card>
                      )}
                    </>
                  )}

                  {!latestAnalysis && !analyzing && (
                    <div
                      style={{
                        textAlign: 'center',
                        padding: '40px 0',
                        color: '#999',
                      }}
                    >
                      <DollarOutlined
                        style={{ fontSize: 40, marginBottom: 16 }}
                      />
                      <br />
                      <Text type="secondary">
                        暂无分析结果，请先添加竞品数据后点击&ldquo;开始分析&rdquo;
                      </Text>
                    </div>
                  )}
                </Space>
              </Card>
            </Col>
          </Row>
        </>
      )}

      {!selectedProductId && (
        <Card>
          <div
            style={{
              textAlign: 'center',
              padding: '60px 0',
              color: '#999',
            }}
          >
            <DollarOutlined style={{ fontSize: 48, marginBottom: 16 }} />
            <br />
            <Text type="secondary" style={{ fontSize: 16 }}>
              请先选择一个商品开始定价分析
            </Text>
          </div>
        </Card>
      )}

      {/* 添加竞品弹窗 */}
      <Modal
        title="添加竞品"
        open={addModalOpen}
        onCancel={() => {
          setAddModalOpen(false);
          addForm.resetFields();
        }}
        onOk={handleAddCompetitor}
        confirmLoading={adding}
        okText="添加"
      >
        <Form form={addForm} layout="vertical">
          <Form.Item
            name="competitor_name"
            label="竞品名称"
            rules={[{ required: true, message: '请输入竞品名称' }]}
          >
            <Input placeholder="请输入竞品名称" maxLength={256} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="competitor_price"
                label="竞品价格"
                rules={[{ required: true, message: '请输入竞品价格' }]}
              >
                <InputNumber
                  min={0}
                  precision={2}
                  prefix="¥"
                  style={{ width: '100%' }}
                  placeholder="0.00"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="competitor_sales" label="竞品销量">
                <InputNumber
                  min={0}
                  style={{ width: '100%' }}
                  placeholder="0"
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="competitor_platform" label="竞品平台">
            <Select
              placeholder="选择平台"
              allowClear
              options={[
                { value: '淘宝', label: '淘宝' },
                { value: '京东', label: '京东' },
                { value: '拼多多', label: '拼多多' },
                { value: '抖音', label: '抖音' },
                { value: '其他', label: '其他' },
              ]}
            />
          </Form.Item>
          <Form.Item name="competitor_url" label="竞品链接">
            <Input placeholder="https://..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* 分析历史弹窗 */}
      <Modal
        title="定价分析历史"
        open={historyOpen}
        onCancel={() => setHistoryOpen(false)}
        footer={null}
        width={900}
      >
        <Table
          columns={historyColumns}
          dataSource={analysisHistory}
          rowKey="id"
          loading={loadingHistory}
          size="small"
          pagination={{
            current: historyPage,
            pageSize: 10,
            total: historyTotal,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p) => setHistoryPage(p),
            size: 'small',
          }}
        />
      </Modal>
    </div>
  );
}

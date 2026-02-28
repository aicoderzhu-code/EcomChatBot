'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Button, Input, Select, Space, Tag, Image, message,
  Typography, Row, Col, Spin, Empty, List,
} from 'antd';
import {
  FileImageOutlined, SendOutlined, ReloadOutlined,
  CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined,
  ClockCircleOutlined, CloudUploadOutlined,
} from '@ant-design/icons';
import { contentApi, type GenerationTask, type GeneratedAsset, type ProductPrompt } from '@/lib/api/content';
import { productApi } from '@/lib/api/product';
import { settingsApi, type ModelConfig } from '@/lib/api/settings';
import { usePlatformUpload } from '@/hooks/usePlatformUpload';
import type { Product } from '@/types';

const { TextArea } = Input;
const { Title, Text } = Typography;

const SIZE_OPTIONS = [
  { value: '1024x1024', label: '1024x1024 (正方形)' },
  { value: '1024x1792', label: '1024x1792 (竖版)' },
  { value: '1792x1024', label: '1792x1024 (横版)' },
  { value: '512x512', label: '512x512 (小图)' },
];
const COUNT_OPTIONS = [
  { value: 1, label: '1 张' },
  { value: 2, label: '2 张' },
  { value: 4, label: '4 张' },
];

export default function PosterPage() {
  const [prompt, setPrompt] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<number | undefined>();
  const [selectedPrompt, setSelectedPrompt] = useState<number | undefined>();
  const [selectedModel, setSelectedModel] = useState<number | undefined>();
  const [imageSize, setImageSize] = useState('1024x1024');
  const [imageCount, setImageCount] = useState(1);
  const [generating, setGenerating] = useState(false);

  const [tasks, setTasks] = useState<GenerationTask[]>([]);
  const [assets, setAssets] = useState<GeneratedAsset[]>([]);
  const [prompts, setPrompts] = useState<ProductPrompt[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [imageModels, setImageModels] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [tasksResp, assetsResp, productsResp, modelsResp] = await Promise.all([
        contentApi.listTasks({ task_type: 'poster', size: 10 }),
        contentApi.listAssets({ asset_type: 'image', size: 20 }),
        productApi.listProducts({ status: 'active', size: 100 }),
        settingsApi.getModelConfigsByType('image_generation'),
      ]);
      if (tasksResp.success && tasksResp.data) setTasks(tasksResp.data.items);
      if (assetsResp.success && assetsResp.data) setAssets(assetsResp.data.items);
      if (productsResp.success && productsResp.data) setProducts(productsResp.data.items);
      if (modelsResp.success && modelsResp.data) setImageModels(modelsResp.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // 任务状态轮询
  useEffect(() => {
    const hasPending = tasks.some(t => ['pending', 'processing'].includes(t.status));
    if (!hasPending) return;
    const timer = setInterval(loadData, 5000);
    return () => clearInterval(timer);
  }, [tasks, loadData]);

  useEffect(() => {
    if (selectedProduct) {
      contentApi.listPrompts({ product_id: selectedProduct, prompt_type: 'image', size: 100 })
        .then(resp => { if (resp.success && resp.data) setPrompts(resp.data.items); })
        .catch(() => {});
    } else {
      setPrompts([]);
      setSelectedPrompt(undefined);
    }
  }, [selectedProduct]);

  const { uploadAsset } = usePlatformUpload(loadData);

  const handleGenerate = async () => {
    if (!prompt.trim()) { message.warning('请输入生成提示词'); return; }
    setGenerating(true);
    try {
      const resp = await contentApi.createGeneration({
        task_type: 'poster',
        prompt: prompt.trim(),
        product_id: selectedProduct,
        prompt_id: selectedPrompt,
        model_config_id: selectedModel,
        params: { size: imageSize, n: imageCount },
      });
      if (resp.success) { message.success('海报生成任务已创建'); setPrompt(''); loadData(); }
      else { message.error(resp.error?.message || '创建失败'); }
    } catch { message.error('创建任务失败'); }
    finally { setGenerating(false); }
  };

  const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
    pending: { color: 'default', icon: <ClockCircleOutlined />, text: '等待中' },
    processing: { color: 'processing', icon: <LoadingOutlined />, text: '生成中' },
    completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
    failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' },
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        <FileImageOutlined style={{ marginRight: 8 }} />
        海报生成工作台
      </Title>
      <Row gutter={24}>
        <Col span={10}>
          <Card title="生成配置">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <Text strong>关联商品（可选）</Text>
                <Select placeholder="选择商品" allowClear style={{ width: '100%', marginTop: 8 }}
                  value={selectedProduct} onChange={(val) => { setSelectedProduct(val); setSelectedPrompt(undefined); }}
                  showSearch optionFilterProp="label" options={products.map(p => ({ value: p.id, label: p.title }))} />
              </div>
              {selectedProduct && prompts.length > 0 && (
                <div>
                  <Text strong>使用提示词（可选）</Text>
                  <Select placeholder="选择提示词" allowClear style={{ width: '100%', marginTop: 8 }}
                    value={selectedPrompt} onChange={(val) => { setSelectedPrompt(val); if (val) { const p = prompts.find(p => p.id === val); if (p) setPrompt(p.content); } }}
                    options={prompts.map(p => ({ value: p.id, label: p.name }))} />
                </div>
              )}
              <div>
                <Text strong>图像生成模型（可选）</Text>
                <Select placeholder="选择图像生成模型（不选则使用默认）" allowClear style={{ width: '100%', marginTop: 8 }}
                  value={selectedModel} onChange={setSelectedModel}
                  options={imageModels.map(m => ({ value: m.id, label: `${m.provider} / ${m.model_name}${m.is_default ? ' (默认)' : ''}` }))} />
              </div>
              <Row gutter={12}>
                <Col span={14}>
                  <Text strong>图片尺寸</Text>
                  <Select style={{ width: '100%', marginTop: 8 }} value={imageSize} onChange={setImageSize} options={SIZE_OPTIONS} />
                </Col>
                <Col span={10}>
                  <Text strong>生成数量</Text>
                  <Select style={{ width: '100%', marginTop: 8 }} value={imageCount} onChange={setImageCount} options={COUNT_OPTIONS} />
                </Col>
              </Row>
              <div>
                <Text strong>生成提示词</Text>
                <TextArea rows={6} value={prompt} onChange={e => setPrompt(e.target.value)}
                  placeholder="描述你想要的海报风格、内容、色调等..." style={{ marginTop: 8 }} />
              </div>
              <Button type="primary" icon={<SendOutlined />} loading={generating} onClick={handleGenerate} block size="large">
                生成海报
              </Button>
            </Space>
          </Card>
          <Card title="最近任务" style={{ marginTop: 16 }}>
            <List loading={loading} dataSource={tasks}
              renderItem={(task) => {
                const sc = statusConfig[task.status] || statusConfig.pending;
                return (
                  <List.Item actions={[task.status === 'failed' && (
                    <Button key="retry" size="small" icon={<ReloadOutlined />} onClick={() => contentApi.retryTask(task.id).then(loadData)}>重试</Button>
                  )].filter(Boolean)}>
                    <List.Item.Meta
                      title={<Space><Tag icon={sc.icon} color={sc.color}>{sc.text}</Tag><Text ellipsis style={{ maxWidth: 200 }}>{task.prompt}</Text></Space>}
                      description={
                        <Space direction="vertical" size={0}>
                          <span>{`结果: ${task.result_count} 张 | ${new Date(task.created_at).toLocaleString('zh-CN')}`}</span>
                          {task.status === 'failed' && task.error_message && (
                            <Text type="danger" style={{ fontSize: 12 }}>{task.error_message}</Text>
                          )}
                        </Space>
                      }
                    />
                  </List.Item>
                );
              }}
              locale={{ emptyText: <Empty description="暂无任务" /> }}
            />
          </Card>
        </Col>
        <Col span={14}>
          <Card title="生成结果">
            {loading ? (
              <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
            ) : assets.length === 0 ? (
              <Empty description="暂无生成结果" />
            ) : (
              <Row gutter={[16, 16]}>
                {assets.map((asset) => (
                  <Col key={asset.id} span={8}>
                    <Card size="small" hoverable
                      cover={asset.file_url ? (<Image src={asset.file_url} alt="生成海报" style={{ height: 200, objectFit: 'cover' }} />) : null}
                      actions={[
                        <Button key="upload" type="link" size="small" icon={<CloudUploadOutlined />}
                          disabled={!!asset.platform_url} onClick={() => uploadAsset(asset.id)}>
                          {asset.platform_url ? '已上传' : '上传到平台'}
                        </Button>,
                      ]}>
                      <Card.Meta description={<Text type="secondary" style={{ fontSize: 12 }}>{new Date(asset.created_at).toLocaleString('zh-CN')}</Text>} />
                    </Card>
                  </Col>
                ))}
              </Row>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

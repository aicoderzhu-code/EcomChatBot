'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Button, Input, Select, Space, Tag, Image, message,
  Typography, Row, Col, Spin, Empty, Modal, List,
} from 'antd';
import {
  FileImageOutlined, SendOutlined, ReloadOutlined,
  CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { contentApi, type GenerationTask, type GeneratedAsset, type PromptTemplate } from '@/lib/api/content';
import { productApi } from '@/lib/api/product';
import type { Product } from '@/types';

const { TextArea } = Input;
const { Title, Text } = Typography;

export default function PosterPage() {
  const [prompt, setPrompt] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<number | undefined>();
  const [selectedTemplate, setSelectedTemplate] = useState<number | undefined>();
  const [generating, setGenerating] = useState(false);

  const [tasks, setTasks] = useState<GenerationTask[]>([]);
  const [assets, setAssets] = useState<GeneratedAsset[]>([]);
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);

  // 模板管理弹窗
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [newTemplateName, setNewTemplateName] = useState('');
  const [newTemplateContent, setNewTemplateContent] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [tasksResp, assetsResp, templatesResp, productsResp] = await Promise.all([
        contentApi.listTasks({ task_type: 'poster', size: 10 }),
        contentApi.listAssets({ asset_type: 'image', size: 20 }),
        contentApi.listTemplates({ template_type: 'poster' }),
        productApi.listProducts({ status: 'active', size: 100 }),
      ]);
      if (tasksResp.success && tasksResp.data) setTasks(tasksResp.data.items);
      if (assetsResp.success && assetsResp.data) setAssets(assetsResp.data.items);
      if (templatesResp.success && templatesResp.data) setTemplates(templatesResp.data.items);
      if (productsResp.success && productsResp.data) setProducts(productsResp.data.items);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      message.warning('请输入生成提示词');
      return;
    }
    setGenerating(true);
    try {
      const resp = await contentApi.createGeneration({
        task_type: 'poster',
        prompt: prompt.trim(),
        product_id: selectedProduct,
        template_id: selectedTemplate,
      });
      if (resp.success) {
        message.success('海报生成任务已创建');
        setPrompt('');
        loadData();
      } else {
        message.error(resp.error?.message || '创建失败');
      }
    } catch {
      message.error('创建任务失败');
    } finally {
      setGenerating(false);
    }
  };

  const handleCreateTemplate = async () => {
    if (!newTemplateName || !newTemplateContent) return;
    try {
      const resp = await contentApi.createTemplate({
        name: newTemplateName,
        template_type: 'poster',
        content: newTemplateContent,
      });
      if (resp.success) {
        message.success('模板创建成功');
        setTemplateModalOpen(false);
        setNewTemplateName('');
        setNewTemplateContent('');
        loadData();
      }
    } catch {
      message.error('创建模板失败');
    }
  };

  const handleUploadToPlatform = async (assetId: number) => {
    try {
      const resp = await contentApi.uploadAssetToPlatform({
        asset_id: assetId,
        platform_config_id: 1,
      });
      if (resp.success) {
        message.success('已上传到平台');
        loadData();
      } else {
        message.error(resp.error?.message || '上传失败');
      }
    } catch {
      message.error('上传失败');
    }
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
        {/* 左侧：输入区 */}
        <Col span={10}>
          <Card title="生成配置">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <Text strong>关联商品（可选）</Text>
                <Select
                  placeholder="选择商品"
                  allowClear
                  style={{ width: '100%', marginTop: 8 }}
                  value={selectedProduct}
                  onChange={setSelectedProduct}
                  showSearch
                  optionFilterProp="label"
                  options={products.map(p => ({ value: p.id, label: p.title }))}
                />
              </div>

              <div>
                <Text strong>使用模板（可选）</Text>
                <Space style={{ width: '100%', marginTop: 8 }}>
                  <Select
                    placeholder="选择模板"
                    allowClear
                    style={{ flex: 1 }}
                    value={selectedTemplate}
                    onChange={(val) => {
                      setSelectedTemplate(val);
                      if (val) {
                        const t = templates.find(t => t.id === val);
                        if (t) setPrompt(t.content);
                      }
                    }}
                    options={templates.map(t => ({ value: t.id, label: t.name }))}
                  />
                  <Button onClick={() => setTemplateModalOpen(true)}>新建模板</Button>
                </Space>
              </div>

              <div>
                <Text strong>生成提示词</Text>
                <TextArea
                  rows={6}
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  placeholder="描述你想要的海报风格、内容、色调等..."
                  style={{ marginTop: 8 }}
                />
              </div>

              <Button
                type="primary"
                icon={<SendOutlined />}
                loading={generating}
                onClick={handleGenerate}
                block
                size="large"
              >
                生成海报
              </Button>
            </Space>
          </Card>

          {/* 最近任务 */}
          <Card title="最近任务" style={{ marginTop: 16 }}>
            <List
              loading={loading}
              dataSource={tasks}
              renderItem={(task) => {
                const sc = statusConfig[task.status] || statusConfig.pending;
                return (
                  <List.Item
                    actions={[
                      task.status === 'failed' && (
                        <Button
                          key="retry"
                          size="small"
                          icon={<ReloadOutlined />}
                          onClick={() => contentApi.retryTask(task.id).then(loadData)}
                        >
                          重试
                        </Button>
                      ),
                    ].filter(Boolean)}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Tag icon={sc.icon} color={sc.color}>{sc.text}</Tag>
                          <Text ellipsis style={{ maxWidth: 200 }}>{task.prompt}</Text>
                        </Space>
                      }
                      description={`结果: ${task.result_count} 张 | ${new Date(task.created_at).toLocaleString('zh-CN')}`}
                    />
                  </List.Item>
                );
              }}
              locale={{ emptyText: <Empty description="暂无任务" /> }}
            />
          </Card>
        </Col>

        {/* 右侧：结果展示区 */}
        <Col span={14}>
          <Card title="生成结果">
            {loading ? (
              <div style={{ textAlign: 'center', padding: 60 }}>
                <Spin size="large" />
              </div>
            ) : assets.length === 0 ? (
              <Empty description="暂无生成结果" />
            ) : (
              <Row gutter={[16, 16]}>
                {assets.map((asset) => (
                  <Col key={asset.id} span={8}>
                    <Card
                      size="small"
                      hoverable
                      cover={
                        asset.file_url ? (
                          <Image
                            src={asset.file_url}
                            alt="生成海报"
                            style={{ height: 200, objectFit: 'cover' }}
                          />
                        ) : null
                      }
                      actions={[
                        <Button
                          key="upload"
                          type="link"
                          size="small"
                          disabled={!!asset.platform_url}
                          onClick={() => handleUploadToPlatform(asset.id)}
                        >
                          {asset.platform_url ? '已上传' : '上传到平台'}
                        </Button>,
                      ]}
                    >
                      <Card.Meta
                        description={
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {new Date(asset.created_at).toLocaleString('zh-CN')}
                          </Text>
                        }
                      />
                    </Card>
                  </Col>
                ))}
              </Row>
            )}
          </Card>
        </Col>
      </Row>

      {/* 新建模板弹窗 */}
      <Modal
        title="新建海报提示词模板"
        open={templateModalOpen}
        onCancel={() => setTemplateModalOpen(false)}
        onOk={handleCreateTemplate}
        okText="创建"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Input
            placeholder="模板名称"
            value={newTemplateName}
            onChange={e => setNewTemplateName(e.target.value)}
          />
          <TextArea
            rows={6}
            placeholder="模板内容，可使用变量如 {{product_title}}、{{product_description}}"
            value={newTemplateContent}
            onChange={e => setNewTemplateContent(e.target.value)}
          />
        </Space>
      </Modal>
    </div>
  );
}

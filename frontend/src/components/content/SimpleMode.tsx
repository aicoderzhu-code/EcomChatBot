'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Steps,
  Card,
  Button,
  Select,
  Space,
  message,
  Tabs,
  Typography,
  Input,
  Row,
  Col,
  Image,
  Tag,
} from 'antd';
import {
  ArrowLeftOutlined,
  ArrowRightOutlined,
  SendOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { contentApi } from '@/lib/api/content';
import { productApi } from '@/lib/api/product';
import type {
  ContentTemplate,
  Product,
  GenerationTask,
  GeneratedAsset,
  SceneType,
} from '@/types';
import TemplateGrid from '@/components/content/TemplateGrid';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface SimpleModeProps {
  category: 'poster' | 'video';
}

export default function SimpleMode({ category }: SimpleModeProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  // Step 1: 选择模板
  const [templates, setTemplates] = useState<ContentTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<ContentTemplate | null>(null);
  const [sceneType, setSceneType] = useState<SceneType>('main_image');

  // Step 2: 选择商品和平台
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<number | undefined>();
  const [targetPlatform, setTargetPlatform] = useState<string>('taobao');
  const [renderedPrompt, setRenderedPrompt] = useState('');
  const [editablePrompt, setEditablePrompt] = useState('');

  // Step 3: 生成结果
  const [task, setTask] = useState<GenerationTask | null>(null);
  const [assets, setAssets] = useState<GeneratedAsset[]>([]);

  // 场景类型选项
  const sceneTypeOptions = category === 'poster'
    ? [
        { value: 'main_image', label: '商品主图' },
        { value: 'detail_image', label: '详情图' },
        { value: 'promo_poster', label: '促销海报' },
      ]
    : [
        { value: 'main_video', label: '商品主图视频' },
        { value: 'short_video', label: '短视频' },
        { value: 'detail_video', label: '详情视频' },
      ];

  // 平台选项
  const platformOptions = [
    { value: 'taobao', label: '淘宝' },
    { value: 'pdd', label: '拼多多' },
    { value: 'douyin', label: '抖音' },
    { value: 'jd', label: '京东' },
    { value: 'kuaishou', label: '快手' },
  ];

  // 加载模板
  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await contentApi.listTemplates({
        category,
        scene_type: sceneType,
        size: 50,
      });
      if (resp.success && resp.data) {
        setTemplates(resp.data.items);
      }
    } catch {
      message.error('加载模板失败');
    } finally {
      setLoading(false);
    }
  }, [category, sceneType]);

  // 加载商品
  const loadProducts = useCallback(async () => {
    try {
      const resp = await productApi.listProducts({ status: 'active', size: 100 });
      if (resp.success && resp.data) {
        setProducts(resp.data.items);
      }
    } catch {
      message.error('加载商品失败');
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  useEffect(() => {
    if (currentStep === 1) {
      loadProducts();
    }
  }, [currentStep, loadProducts]);

  // 渲染模板
  const handleRenderTemplate = useCallback(async () => {
    if (!selectedTemplate || !selectedProduct) return;

    setLoading(true);
    try {
      const resp = await contentApi.renderTemplate(selectedTemplate.id, {
        product_id: selectedProduct,
        target_platform: targetPlatform,
      });
      if (resp.success && resp.data) {
        setRenderedPrompt(resp.data.rendered_prompt);
        setEditablePrompt(resp.data.rendered_prompt);
      }
    } catch {
      message.error('渲染模板失败');
    } finally {
      setLoading(false);
    }
  }, [selectedTemplate, selectedProduct, targetPlatform]);

  useEffect(() => {
    if (currentStep === 1 && selectedTemplate && selectedProduct) {
      handleRenderTemplate();
    }
  }, [currentStep, selectedTemplate, selectedProduct, handleRenderTemplate]);

  // 生成内容
  const handleGenerate = useCallback(async () => {
    if (!selectedTemplate || !selectedProduct) {
      message.warning('请选择模板和商品');
      return;
    }

    setGenerating(true);
    try {
      const resp = await contentApi.createGeneration({
        task_type: category,
        prompt: editablePrompt,
        product_id: selectedProduct,
        template_id: selectedTemplate.id,
        scene_type: sceneType,
        target_platform: targetPlatform,
        generation_mode: 'simple',
      });

      if (resp.success && resp.data) {
        setTask(resp.data);
        setCurrentStep(2);
        message.success('生成任务已创建');
        // 开始轮询任务状态
        pollTaskStatus(resp.data.id);
      }
    } catch {
      message.error('创建生成任务失败');
    } finally {
      setGenerating(false);
    }
  }, [selectedTemplate, selectedProduct, editablePrompt, category, sceneType, targetPlatform]);

  // 轮询任务状态
  const pollTaskStatus = useCallback(async (taskId: number) => {
    const poll = async () => {
      try {
        const taskResp = await contentApi.getTask(taskId);
        if (taskResp.success && taskResp.data) {
          setTask(taskResp.data);

          if (taskResp.data.status === 'completed') {
            // 加载生成的素材
            const assetsResp = await contentApi.listAssets({ task_id: taskId });
            if (assetsResp.success && assetsResp.data) {
              setAssets(assetsResp.data.items);
            }
            return true; // 停止轮询
          } else if (taskResp.data.status === 'failed') {
            message.error(`生成失败: ${taskResp.data.error_message}`);
            return true; // 停止轮询
          }
        }
        return false; // 继续轮询
      } catch {
        return true; // 停止轮询
      }
    };

    // 轮询逻辑
    const interval = setInterval(async () => {
      const shouldStop = await poll();
      if (shouldStop) {
        clearInterval(interval);
      }
    }, 3000);

    // 初始调用
    poll();
  }, []);

  // 步骤导航
  const handleNext = () => {
    if (currentStep === 0 && !selectedTemplate) {
      message.warning('请选择一个模板');
      return;
    }
    if (currentStep === 1 && !selectedProduct) {
      message.warning('请选择一个商品');
      return;
    }
    setCurrentStep(currentStep + 1);
  };

  const handlePrev = () => {
    setCurrentStep(currentStep - 1);
  };

  const handleReset = () => {
    setCurrentStep(0);
    setSelectedTemplate(null);
    setSelectedProduct(undefined);
    setTask(null);
    setAssets([]);
  };

  // 渲染步骤内容
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <Title level={4}>选择场景模板</Title>
              <Tabs
                activeKey={sceneType}
                onChange={(key) => setSceneType(key as SceneType)}
                items={sceneTypeOptions.map((opt) => ({
                  key: opt.value,
                  label: opt.label,
                }))}
              />
            </div>
            <TemplateGrid
              templates={templates}
              selectedTemplate={selectedTemplate}
              onSelectTemplate={setSelectedTemplate}
              loading={loading}
            />
          </div>
        );

      case 1:
        return (
          <div className="space-y-6">
            <Card title="选择商品和目标平台">
              <Space direction="vertical" className="w-full" size="large">
                <div>
                  <Text strong>选择商品</Text>
                  <Select
                    className="w-full mt-2"
                    placeholder="请选择商品"
                    value={selectedProduct}
                    onChange={setSelectedProduct}
                    showSearch
                    optionFilterProp="label"
                    options={products.map((p) => ({
                      value: p.id,
                      label: p.title,
                    }))}
                  />
                </div>

                <div>
                  <Text strong>目标平台</Text>
                  <Select
                    className="w-full mt-2"
                    value={targetPlatform}
                    onChange={setTargetPlatform}
                    options={platformOptions}
                  />
                </div>
              </Space>
            </Card>

            {renderedPrompt && (
              <Card title="提示词预览">
                <Space direction="vertical" className="w-full" size="middle">
                  <div>
                    <Text type="secondary">自动渲染的提示词（可编辑）：</Text>
                    <TextArea
                      className="mt-2"
                      value={editablePrompt}
                      onChange={(e) => setEditablePrompt(e.target.value)}
                      rows={4}
                    />
                  </div>

                  {selectedTemplate?.platform_presets?.[targetPlatform] && (
                    <div>
                      <Text type="secondary">平台规范：</Text>
                      <div className="mt-2">
                        <Tag color="blue">
                          尺寸: {selectedTemplate.platform_presets[targetPlatform].size}
                        </Tag>
                      </div>
                    </div>
                  )}
                </Space>
              </Card>
            )}
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            <Card title="生成状态">
              {task && (
                <Space direction="vertical" className="w-full">
                  <div className="flex items-center justify-between">
                    <Text>任务状态：</Text>
                    <Tag
                      color={
                        task.status === 'completed'
                          ? 'success'
                          : task.status === 'failed'
                          ? 'error'
                          : 'processing'
                      }
                    >
                      {task.status === 'pending' && '等待中'}
                      {task.status === 'processing' && '生成中'}
                      {task.status === 'completed' && '已完成'}
                      {task.status === 'failed' && '失败'}
                    </Tag>
                  </div>
                  {task.error_message && (
                    <Text type="danger">{task.error_message}</Text>
                  )}
                </Space>
              )}
            </Card>

            {assets.length > 0 && (
              <Card title="生成结果">
                <Row gutter={[16, 16]}>
                  {assets.map((asset) => (
                    <Col key={asset.id} xs={24} sm={12} md={8} lg={6}>
                      <Card
                        hoverable
                        cover={
                          asset.file_url && (
                            <Image
                              src={asset.file_url}
                              alt="Generated"
                              className="h-48 object-cover"
                            />
                          )
                        }
                        actions={[
                          <Button
                            key="download"
                            type="link"
                            href={contentApi.getAssetDownloadUrl(asset.id)}
                            target="_blank"
                          >
                            下载
                          </Button>,
                        ]}
                      />
                    </Col>
                  ))}
                </Row>
              </Card>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <Steps
        current={currentStep}
        items={[
          { title: '选择模板' },
          { title: '配置参数' },
          { title: '生成结果' },
        ]}
      />

      <div className="mt-6">{renderStepContent()}</div>

      <div className="flex justify-between mt-6">
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={handlePrev}
          disabled={currentStep === 0}
        >
          上一步
        </Button>

        <Space>
          {currentStep === 2 && (
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              重新开始
            </Button>
          )}

          {currentStep < 2 ? (
            currentStep === 1 ? (
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleGenerate}
                loading={generating}
              >
                开始生成
              </Button>
            ) : (
              <Button
                type="primary"
                icon={<ArrowRightOutlined />}
                onClick={handleNext}
              >
                下一步
              </Button>
            )
          ) : null}
        </Space>
      </div>
    </div>
  );
}



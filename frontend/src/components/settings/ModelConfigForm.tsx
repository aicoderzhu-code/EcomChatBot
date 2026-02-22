'use client';

import { useState, useEffect } from 'react';
import {
  Form,
  Select,
  Input,
  Slider,
  Button,
  Card,
  Typography,
  message,
  Space,
  Spin,
} from 'antd';
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons';
import { LLMConfig } from '@/types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface ModelConfigFormProps {
  initialConfig?: LLMConfig;
  loading?: boolean;
  onSave: (config: LLMConfig) => Promise<void>;
}

const defaultConfig: LLMConfig = {
  provider: 'openai',
  api_key: '',
  model_name: 'gpt-4o',
  temperature: 0.7,
  system_prompt: `你是一个专业的电商客服助手。
请始终保持礼貌、专业。
回答要简洁明了。
如果遇到无法回答的问题，请引导用户转接人工客服。
不要编造事实，严格基于提供的上下文回答。`,
};

const providerModels: Record<string, string[]> = {
  openai: ['gpt-4o', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo'],
  anthropic: ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
  zhipu: ['glm-4', 'glm-4v', 'glm-3-turbo'],
  deepseek: ['deepseek-chat', 'deepseek-coder'],
};

export default function ModelConfigForm({
  initialConfig,
  loading = false,
  onSave,
}: ModelConfigFormProps) {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [provider, setProvider] = useState<string>(
    initialConfig?.provider || defaultConfig.provider
  );
  const [temperature, setTemperature] = useState(
    initialConfig?.temperature || defaultConfig.temperature
  );

  useEffect(() => {
    if (initialConfig) {
      form.setFieldsValue(initialConfig);
      setProvider(initialConfig.provider);
      setTemperature(initialConfig.temperature);
    }
  }, [initialConfig, form]);

  const handleProviderChange = (value: string) => {
    setProvider(value);
    // Reset model to first available for new provider
    const models = providerModels[value];
    if (models && models.length > 0) {
      form.setFieldValue('model_name', models[0]);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await onSave(values as LLMConfig);
      message.success('配置保存成功');
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    form.setFieldsValue(defaultConfig);
    setProvider(defaultConfig.provider);
    setTemperature(defaultConfig.temperature);
    message.info('已重置为默认配置');
  };

  if (loading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-12">
          <Spin tip="加载配置中..." />
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <Title level={5} className="mb-2">
        LLM 模型配置
      </Title>
      <Paragraph type="secondary" className="mb-6">
        配置用于智能回复的底层大语言模型参数。
      </Paragraph>

      <Form
        form={form}
        layout="vertical"
        initialValues={initialConfig || defaultConfig}
      >
        <Form.Item
          name="provider"
          label="模型提供商 (Provider)"
          rules={[{ required: true, message: '请选择模型提供商' }]}
        >
          <Select onChange={handleProviderChange}>
            <Option value="openai">OpenAI (GPT-4/3.5)</Option>
            <Option value="anthropic">Anthropic (Claude 3)</Option>
            <Option value="zhipu">智谱 AI (GLM-4)</Option>
            <Option value="deepseek">DeepSeek</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="api_key"
          label="API Key"
          rules={[{ required: true, message: '请输入 API Key' }]}
          extra={
            <Text type="secondary" className="text-xs">
              密钥将加密存储，不会明文显示。
            </Text>
          }
        >
          <Input.Password placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxx" />
        </Form.Item>

        <Form.Item
          name="model_name"
          label="模型名称"
          rules={[{ required: true, message: '请选择模型' }]}
        >
          <Select>
            {(providerModels[provider] || []).map((model) => (
              <Option key={model} value={model}>
                {model}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="temperature"
          label={`温度 (Temperature): ${temperature}`}
        >
          <Slider
            min={0}
            max={1}
            step={0.1}
            value={temperature}
            onChange={setTemperature}
            marks={{
              0: '精确 (0.0)',
              0.5: '平衡',
              1: '创造性 (1.0)',
            }}
          />
        </Form.Item>

        <Form.Item
          name="system_prompt"
          label="系统提示词 (System Prompt)"
          rules={[{ required: true, message: '请输入系统提示词' }]}
        >
          <TextArea
            rows={6}
            placeholder="请输入系统提示词..."
            style={{ fontFamily: 'monospace' }}
          />
        </Form.Item>

        <Form.Item className="mb-0 mt-6">
          <Space>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saving}
            >
              保存配置
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              重置默认
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
}

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Input,
  Button,
  Typography,
  message,
  Space,
  Divider,
  Collapse,
  Row,
  Col,
} from 'antd';
import { SaveOutlined, SettingOutlined } from '@ant-design/icons';
import { settingsApi, DiscoveredModel } from '@/lib/api/settings';
import { ModelProvider, ModelType } from '@/types';
import Skeleton from '@/components/ui/Loading/Skeleton';
import ProviderCard from './ProviderCard';
import ApiKeyValidator, { type ValidationStatus } from './ApiKeyValidator';
import DiscoveredModelsList from './DiscoveredModelsList';
import ModelSelector from './ModelSelector';

const { Title, Text, Paragraph } = Typography;

// ── 平台目录 ──────────────────────────────────────────────────────────────

interface PlatformInfo {
  name: string;
  description: string;
  supportedTypes: ModelType[];
  needsApiBase?: boolean;
}

const PLATFORM_CATALOG: Record<string, PlatformInfo> = {
  openai: {
    name: 'OpenAI',
    description: 'GPT-4o / GPT-3.5 等',
    supportedTypes: ['llm', 'embedding'],
    needsApiBase: true,
  },
  qwen: {
    name: '通义千问',
    description: 'Qwen-Max / Plus / Turbo',
    supportedTypes: ['llm', 'embedding', 'rerank'],
    needsApiBase: true,
  },
  deepseek: {
    name: 'DeepSeek',
    description: 'DeepSeek-Chat / Reasoner',
    supportedTypes: ['llm'],
    needsApiBase: true,
  },
  zhipuai: {
    name: '智谱 AI',
    description: 'GLM-4 系列',
    supportedTypes: ['llm', 'embedding'],
  },
  google: {
    name: 'Google Gemini',
    description: 'Gemini 2.0 / 1.5 系列',
    supportedTypes: ['llm', 'embedding'],
  },
  meta: {
    name: 'Meta (自定义)',
    description: 'Llama 系列，自定义 base URL',
    supportedTypes: ['llm'],
    needsApiBase: true,
  },
  siliconflow: {
    name: '硅基流动',
    description: 'SiliconFlow 开源模型',
    supportedTypes: ['llm', 'embedding', 'rerank', 'image_generation', 'video_generation'],
    needsApiBase: true,
  },
  private: {
    name: '私有部署',
    description: '私有/自托管模型',
    supportedTypes: [],
    needsApiBase: true,
  },
};

const DISCOVER_CAPABLE_PROVIDERS = new Set(['openai', 'qwen', 'deepseek', 'zhipuai', 'google', 'meta', 'siliconflow']);

const ALL_MODEL_TYPES: ModelType[] = ['llm', 'embedding', 'rerank', 'image_generation', 'video_generation'];

// 显示"无可用模型"提示的类型
const SHOW_EMPTY_TYPES: ModelType[] = ['embedding', 'rerank'];

// ── 配置类型 ──────────────────────────────────────────────────────────────

interface PlatformConfig {
  api_key: string;
  api_base: string;
  llm_model: string;
  embedding_model: string;
  rerank_model: string;
  image_generation_model: string;
  video_generation_model: string;
  llm_id?: number;
  embedding_id?: number;
  rerank_id?: number;
  image_generation_id?: number;
  video_generation_id?: number;
}

const MODEL_TYPE_USE_CASE: Record<ModelType, { use_case: string; temperature: number; max_tokens: number }> = {
  llm: { use_case: 'chat', temperature: 0.7, max_tokens: 2000 },
  embedding: { use_case: 'embedding', temperature: 0, max_tokens: 8192 },
  rerank: { use_case: 'rerank', temperature: 0, max_tokens: 0 },
  image_generation: { use_case: 'image_generation', temperature: 0, max_tokens: 0 },
  video_generation: { use_case: 'video_generation', temperature: 0, max_tokens: 0 },
};

// ── 主组件 ────────────────────────────────────────────────────────────────

export default function ModelConfigForm() {
  const [loading, setLoading] = useState(true);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [configs, setConfigs] = useState<Record<string, PlatformConfig>>({});
  const [validationStatus, setValidationStatus] = useState<ValidationStatus>('idle');
  const [validationMsg, setValidationMsg] = useState('');
  const [saving, setSaving] = useState(false);
  const [discoveredModels, setDiscoveredModels] = useState<DiscoveredModel[]>([]);
  const [discovering, setDiscovering] = useState(false);
  const [batchSaving, setBatchSaving] = useState(false);
  const [providerDiscoveredModels, setProviderDiscoveredModels] = useState<Record<string, DiscoveredModel[]>>({});

  // ── 配置加载 ──

  const loadConfigs = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const resp = await settingsApi.getModelConfigs();
      if (resp.success && resp.data) {
        const merged: Record<string, PlatformConfig> = {};
        const discoveredFromSaved: Record<string, DiscoveredModel[]> = {};

        for (const cfg of resp.data) {
          const provider = cfg.provider;

          // 初始化 provider 配置
          if (!merged[provider]) {
            merged[provider] = {
              api_key: '', api_base: '',
              llm_model: '', embedding_model: '', rerank_model: '',
              image_generation_model: '', video_generation_model: '',
            };
          }
          if (cfg.api_key) merged[provider].api_key = cfg.api_key;
          if (cfg.api_base) merged[provider].api_base = cfg.api_base;

          // 按类型分配
          const modelField = `${cfg.model_type}_model` as keyof PlatformConfig;
          const idField = `${cfg.model_type}_id` as keyof PlatformConfig;
          if (modelField in merged[provider]) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (merged[provider] as any)[modelField] = cfg.model_name;
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (merged[provider] as any)[idField] = cfg.id;
          }

          // 重建 discovered models
          if (!discoveredFromSaved[provider]) discoveredFromSaved[provider] = [];
          discoveredFromSaved[provider].push({
            name: cfg.model_name,
            model_type: cfg.model_type as 'llm' | 'embedding' | 'rerank',
          });
        }

        setConfigs(merged);
        setProviderDiscoveredModels(prev => ({ ...prev, ...discoveredFromSaved }));

        if (!silent) {
          const firstConfigured = Object.keys(merged)[0];
          if (firstConfigured) setSelectedProvider(firstConfigured);
        }
      }
    } catch {
      message.error('加载模型配置失败');
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => { loadConfigs(); }, [loadConfigs]);

  // ── 配置操作 ──

  const getConfig = (provider: string): PlatformConfig => {
    return configs[provider] ?? {
      api_key: '', api_base: '',
      llm_model: '', embedding_model: '', rerank_model: '',
      image_generation_model: '', video_generation_model: '',
    };
  };

  const updateConfig = (provider: string, patch: Partial<PlatformConfig>) => {
    setConfigs(prev => ({
      ...prev,
      [provider]: { ...getConfig(provider), ...patch },
    }));
  };

  const handleSelectProvider = (provider: string) => {
    setSelectedProvider(prev => prev === provider ? null : provider);
    setValidationStatus('idle');
    setValidationMsg('');
    setDiscoveredModels([]);
  };

  // ── API Key 验证 ──

  const handleValidate = async () => {
    if (!selectedProvider) return;
    const cfg = getConfig(selectedProvider);

    if (selectedProvider === 'private' && !cfg.api_key.trim()) {
      if (!cfg.api_base?.trim()) {
        message.warning('请先填写 API Base URL');
        return;
      }
      setValidationStatus('valid');
      setValidationMsg('私有部署无需验证');
      return;
    }

    if (!cfg.api_key.trim()) {
      message.warning('请先输入 API Key');
      return;
    }

    setValidationStatus('validating');
    setValidationMsg('');
    try {
      const resp = await settingsApi.validateApiKey(selectedProvider, cfg.api_key, cfg.api_base || undefined);
      if (resp.success && resp.data) {
        setValidationStatus(resp.data.valid ? 'valid' : 'invalid');
        setValidationMsg(resp.data.message);
      } else {
        setValidationStatus('invalid');
        setValidationMsg(resp.error?.message || '验证请求失败');
      }
    } catch {
      setValidationStatus('invalid');
      setValidationMsg('网络请求失败，请检查连接');
    }
  };

  // ── 模型发现 ──

  const handleDiscover = async () => {
    if (!selectedProvider) return;
    const cfg = getConfig(selectedProvider);
    setDiscovering(true);
    setDiscoveredModels([]);
    try {
      const resp = await settingsApi.discoverModels(selectedProvider, cfg.api_key, cfg.api_base || undefined);
      if (resp.success && resp.data) {
        setDiscoveredModels(resp.data.models);
        if (resp.data.models.length === 0) {
          message.warning('未发现可用模型，请检查 API Key 权限');
        }
      } else {
        message.error('模型发现失败');
      }
    } catch {
      message.error('网络请求失败，请检查连接');
    } finally {
      setDiscovering(false);
    }
  };

  const handleBatchSave = async () => {
    if (!selectedProvider || discoveredModels.length === 0) return;
    const cfg = getConfig(selectedProvider);
    setBatchSaving(true);
    try {
      const items = discoveredModels.map(m => ({
        provider: selectedProvider,
        model_name: m.name,
        model_type: m.model_type,
        api_key: cfg.api_key,
        api_base: cfg.api_base || null,
      }));
      const resp = await settingsApi.batchSaveModels(items);
      if (resp.success) {
        message.success(`已保存 ${discoveredModels.length} 个模型配置`);
        setProviderDiscoveredModels(prev => ({ ...prev, [selectedProvider]: discoveredModels }));
        setDiscoveredModels([]);
        await loadConfigs(true);
      } else {
        message.error('批量保存失败，请重试');
      }
    } catch {
      message.error('批量保存失败，请重试');
    } finally {
      setBatchSaving(false);
    }
  };

  // ── 保存配置 ──

  const handleSave = async () => {
    if (!selectedProvider) return;
    const cfg = getConfig(selectedProvider);

    if (selectedProvider === 'private') {
      if (!cfg.api_base?.trim()) {
        message.warning('私有部署需要填写 API Base URL');
        return;
      }
    } else {
      if (!cfg.api_key.trim()) { message.warning('请输入 API Key'); return; }
      if (validationStatus === 'idle') { message.warning('请先验证 API Key 有效性'); return; }
      if (validationStatus === 'invalid') { message.error('API Key 无效，请更正后重试'); return; }
      if (validationStatus === 'validating') { message.warning('正在验证中，请稍候'); return; }
    }

    setSaving(true);
    try {
      const basePayload = {
        provider: selectedProvider as ModelProvider,
        api_key: cfg.api_key,
        api_base: cfg.api_base || null,
        is_default: true,
        priority: 1,
      };

      const discovered = providerDiscoveredModels[selectedProvider] || [];

      for (const modelType of ALL_MODEL_TYPES) {
        const modelField = `${modelType}_model` as keyof PlatformConfig;
        const idField = `${modelType}_id` as keyof PlatformConfig;
        const options = discovered.filter(m => m.model_type === modelType).map(m => m.name);
        const selectedModel = (cfg[modelField] as string) || options[0] || '';

        if (!selectedModel) continue;

        const { use_case, temperature, max_tokens } = MODEL_TYPE_USE_CASE[modelType];
        const payload = {
          ...basePayload,
          model_name: selectedModel,
          model_type: modelType,
          use_case,
          temperature,
          max_tokens,
        };

        const existingId = cfg[idField] as number | undefined;
        if (existingId) {
          await settingsApi.updateModelConfig(existingId, payload);
        } else {
          const res = await settingsApi.createModelConfig(payload);
          if (res.success && res.data) {
            updateConfig(selectedProvider, { [idField]: res.data.id } as Partial<PlatformConfig>);
          }
        }
      }

      message.success(`${PLATFORM_CATALOG[selectedProvider].name} 配置已保存`);
    } catch {
      message.error('保存失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  // ── 辅助函数 ──

  const getModelOptions = (type: ModelType): string[] => {
    if (!selectedProvider) return [];
    return (providerDiscoveredModels[selectedProvider] || [])
      .filter(m => m.model_type === type)
      .map(m => m.name);
  };

  // ── 渲染 ──

  if (loading) {
    return (
      <Card>
        <div className="py-6 px-4 space-y-4">
          <Skeleton variant="text" width="30%" height={24} />
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="border border-neutral-200 rounded-lg p-4">
                <Skeleton variant="circular" width={40} height={40} className="mb-3" />
                <Skeleton variant="text" width="70%" />
                <Skeleton variant="text" width="50%" className="mt-1" />
              </div>
            ))}
          </div>
          <Skeleton variant="rectangular" height={100} className="mt-4" />
        </div>
      </Card>
    );
  }

  const currentCatalog = selectedProvider ? PLATFORM_CATALOG[selectedProvider] : null;
  const currentConfig = selectedProvider ? getConfig(selectedProvider) : null;

  return (
    <div className="space-y-4">
      {/* 平台选择 */}
      <Card>
        <Title level={5} className="mb-1">选择模型平台</Title>
        <Paragraph type="secondary" className="mb-4">
          选择您的 AI 服务提供商，然后配置对应的模型和 API Key。
        </Paragraph>
        <Row gutter={[12, 12]}>
          {Object.entries(PLATFORM_CATALOG).map(([provider, info]) => (
            <Col key={provider} xs={12} sm={8} md={6}>
              <ProviderCard
                provider={provider}
                name={info.name}
                description={info.description}
                supportedTypes={info.supportedTypes}
                isSelected={selectedProvider === provider}
                hasConfig={!!configs[provider]?.api_key}
                onClick={() => handleSelectProvider(provider)}
              />
            </Col>
          ))}
        </Row>
      </Card>

      {/* 平台配置面板 */}
      {selectedProvider && currentCatalog && currentConfig && (
        <Card
          title={
            <Space>
              <SettingOutlined />
              <span>{currentCatalog.name} 配置</span>
            </Space>
          }
          extra={
            <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
              保存配置
            </Button>
          }
        >
          <ApiKeyValidator
            apiKey={currentConfig.api_key}
            onApiKeyChange={v => {
              updateConfig(selectedProvider, { api_key: v });
              setValidationStatus('idle');
              setValidationMsg('');
            }}
            validationStatus={validationStatus}
            validationMsg={validationMsg}
            onValidate={handleValidate}
            canDiscover={DISCOVER_CAPABLE_PROVIDERS.has(selectedProvider)}
            discovering={discovering}
            onDiscover={handleDiscover}
            optional={selectedProvider === 'private'}
          />

          <DiscoveredModelsList
            models={discoveredModels}
            saving={batchSaving}
            onBatchSave={handleBatchSave}
          />

          {/* API Base URL */}
          {selectedProvider === 'private' ? (
            <div className="mb-4">
              <Text strong className="block mb-1">
                API Base URL <Text type="danger">*</Text>
              </Text>
              <Input
                value={currentConfig.api_base}
                onChange={e => updateConfig(selectedProvider, { api_base: e.target.value })}
                placeholder="例如：http://localhost:11434/v1"
              />
            </div>
          ) : currentCatalog.needsApiBase ? (
            <Collapse
              ghost
              size="small"
              className="mb-4"
              items={[{
                key: 'apibase',
                label: <Text type="secondary" style={{ fontSize: 13 }}>自定义 API Base URL（可选，用于代理或兼容接口）</Text>,
                children: (
                  <Input
                    value={currentConfig.api_base}
                    onChange={e => updateConfig(selectedProvider, { api_base: e.target.value })}
                    placeholder="例如：https://your-proxy.com/v1"
                  />
                ),
              }]}
            />
          ) : null}

          <Divider style={{ margin: '12px 0' }} />

          {/* 模型选择器 */}
          {ALL_MODEL_TYPES.map(type => (
            <ModelSelector
              key={type}
              modelType={type}
              options={getModelOptions(type)}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              value={(currentConfig as any)[`${type}_model`] || ''}
              onChange={v => updateConfig(selectedProvider, { [`${type}_model`]: v } as Partial<PlatformConfig>)}
              showEmpty={SHOW_EMPTY_TYPES.includes(type)}
            />
          ))}
        </Card>
      )}
    </div>
  );
}

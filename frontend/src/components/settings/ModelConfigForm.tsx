'use client';

import { useState, useEffect } from 'react';
import {
  Card,
  Select,
  Input,
  Button,
  Typography,
  message,
  Space,
  Spin,
  Alert,
  Tag,
  Divider,
  Collapse,
  Row,
  Col,
} from 'antd';
import {
  SaveOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  SettingOutlined,
  SearchOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { settingsApi, DiscoveredModel } from '@/lib/api/settings';
import { ModelProvider, ModelType } from '@/types';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// ── 平台目录：各提供商支持的模型列表 ──────────────────────────────────────────
interface PlatformInfo {
  name: string;
  description: string;
  llm: string[];
  embedding: string[];
  rerank: string[];
  needsApiBase?: boolean; // 是否支持自定义 API Base
}

const PLATFORM_CATALOG: Record<string, PlatformInfo> = {
  openai: {
    name: 'OpenAI',
    description: 'GPT-4o / GPT-3.5 等',
    llm: [],
    embedding: [],
    rerank: [],
    needsApiBase: true,
  },
  qwen: {
    name: '通义千问',
    description: 'Qwen-Max / Plus / Turbo',
    llm: [],
    embedding: [],
    rerank: [],
    needsApiBase: true,
  },
  deepseek: {
    name: 'DeepSeek',
    description: 'DeepSeek-Chat / Reasoner',
    llm: [],
    embedding: [],
    rerank: [],
    needsApiBase: true,
  },
  zhipuai: {
    name: '智谱 AI',
    description: 'GLM-4 系列',
    llm: [],
    embedding: [],
    rerank: [],
  },
  google: {
    name: 'Google Gemini',
    description: 'Gemini 2.0 / 1.5 系列',
    llm: [],
    embedding: [],
    rerank: [],
  },
  meta: {
    name: 'Meta (自定义)',
    description: 'Llama 系列，自定义 base URL',
    llm: [],
    embedding: [],
    rerank: [],
    needsApiBase: true,
  },
  siliconflow: {
    name: '硅基流动',
    description: 'SiliconFlow 开源模型',
    llm: [],
    embedding: [],
    rerank: [],
    needsApiBase: true,
  },
  private: {
    name: '私有部署',
    description: '私有/自托管模型',
    llm: [],
    embedding: [],
    rerank: [],
    needsApiBase: true,
  },
};

const MODEL_TYPE_LABELS: Record<ModelType, string> = {
  llm: '大语言模型',
  embedding: '嵌入模型',
  rerank: '重排模型',
};

// 支持自动发现模型的提供商
const DISCOVER_CAPABLE_PROVIDERS = new Set(['openai', 'qwen', 'deepseek', 'zhipuai', 'google', 'meta', 'siliconflow']);

// 每个平台的配置状态
interface PlatformConfig {
  api_key: string;
  api_base: string;
  llm_model: string;
  embedding_model: string;
  rerank_model: string;
  // 已保存的记录 ID（用于更新）
  llm_id?: number;
  embedding_id?: number;
  rerank_id?: number;
}

type ValidationStatus = 'idle' | 'validating' | 'valid' | 'invalid';

export default function ModelConfigForm() {
  const [loading, setLoading] = useState(true);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [configs, setConfigs] = useState<Record<string, PlatformConfig>>({});
  const [validationStatus, setValidationStatus] = useState<ValidationStatus>('idle');
  const [validationMsg, setValidationMsg] = useState('');
  const [saving, setSaving] = useState(false);

  // 模型发现相关状态
  const [discoveredModels, setDiscoveredModels] = useState<DiscoveredModel[]>([]);
  const [discovering, setDiscovering] = useState(false);
  const [batchSaving, setBatchSaving] = useState(false);
  // 已保存的发现模型（按 provider 存储，用于填充下方选择器）
  const [providerDiscoveredModels, setProviderDiscoveredModels] = useState<Record<string, DiscoveredModel[]>>({});

  // 初始化：从后端加载已有配置
  const loadConfigs = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const resp = await settingsApi.getModelConfigs();
      if (resp.success && resp.data) {
        const merged: Record<string, PlatformConfig> = {};
        for (const cfg of resp.data) {
          const provider = cfg.provider;
          if (!merged[provider]) {
            merged[provider] = {
              api_key: cfg.api_key || '',
              api_base: cfg.api_base || '',
              llm_model: '',
              embedding_model: '',
              rerank_model: '',
            };
          }
          // 用已有 api_key（同一 provider 共享）
          if (cfg.api_key) merged[provider].api_key = cfg.api_key;
          if (cfg.api_base) merged[provider].api_base = cfg.api_base;

          if (cfg.model_type === 'llm') {
            merged[provider].llm_model = cfg.model_name;
            merged[provider].llm_id = cfg.id;
          } else if (cfg.model_type === 'embedding') {
            merged[provider].embedding_model = cfg.model_name;
            merged[provider].embedding_id = cfg.id;
          } else if (cfg.model_type === 'rerank') {
            merged[provider].rerank_model = cfg.model_name;
            merged[provider].rerank_id = cfg.id;
          }
        }
        setConfigs(merged);

        // 自动展开第一个已有配置的平台（仅初始加载时）
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
  };

  useEffect(() => {
    loadConfigs();
  }, []);

  const getConfig = (provider: string): PlatformConfig => {
    const catalog = PLATFORM_CATALOG[provider];
    return configs[provider] ?? {
      api_key: '',
      api_base: '',
      llm_model: catalog?.llm[0] || '',
      embedding_model: catalog?.embedding[0] || '',
      rerank_model: catalog?.rerank[0] || '',
    };
  };

  const updateConfig = (provider: string, patch: Partial<PlatformConfig>) => {
    setConfigs(prev => ({
      ...prev,
      [provider]: { ...getConfig(provider), ...patch },
    }));
  };

  // 选择平台时重置验证状态
  const handleSelectProvider = (provider: string) => {
    setSelectedProvider(prev => prev === provider ? null : provider);
    setValidationStatus('idle');
    setValidationMsg('');
    setDiscoveredModels([]);
  };

  // 自动发现可用模型
  const handleDiscover = async () => {
    if (!selectedProvider) return;
    const cfg = getConfig(selectedProvider);
    setDiscovering(true);
    setDiscoveredModels([]);
    try {
      const resp = await settingsApi.discoverModels(
        selectedProvider,
        cfg.api_key,
        cfg.api_base || undefined
      );
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

  // 批量保存已发现的模型
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
        // 持久化已发现模型，用于填充下方选择器
        setProviderDiscoveredModels(prev => ({
          ...prev,
          [selectedProvider]: discoveredModels,
        }));
        setDiscoveredModels([]);
        // 重新加载配置以获取保存后的 ID
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

  // 验证 API Key
  const handleValidate = async () => {
    if (!selectedProvider) return;
    const cfg = getConfig(selectedProvider);

    // 私有部署：若无 API Key 但有 API Base，直接标记为有效
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
      const resp = await settingsApi.validateApiKey(
        selectedProvider,
        cfg.api_key,
        cfg.api_base || undefined
      );
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

  // 保存当前平台配置
  const handleSave = async () => {
    if (!selectedProvider) return;
    const cfg = getConfig(selectedProvider);

    // 私有部署：API Key 可选，API Base 必填，无需验证
    if (selectedProvider === 'private') {
      if (!cfg.api_base?.trim()) {
        message.warning('私有部署需要填写 API Base URL');
        return;
      }
    } else {
      if (!cfg.api_key.trim()) {
        message.warning('请输入 API Key');
        return;
      }
      if (validationStatus === 'idle') {
        message.warning('请先验证 API Key 有效性');
        return;
      }
      if (validationStatus === 'invalid') {
        message.error('API Key 无效，请更正后重试');
        return;
      }
      if (validationStatus === 'validating') {
        message.warning('正在验证中，请稍候');
        return;
      }
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

      // 保存 LLM 模型配置
      const llmOptions = (providerDiscoveredModels[selectedProvider] || []).filter(m => m.model_type === 'llm').map(m => m.name);
      const llmModel = cfg.llm_model || llmOptions[0] || '';
      if (llmModel) {
        const llmPayload = {
          ...basePayload,
          model_name: llmModel,
          model_type: 'llm' as ModelType,
          use_case: 'chat',
          temperature: 0.7,
          max_tokens: 2000,
        };
        if (cfg.llm_id) {
          await settingsApi.updateModelConfig(cfg.llm_id, llmPayload);
        } else {
          const res = await settingsApi.createModelConfig(llmPayload);
          if (res.success && res.data) {
            updateConfig(selectedProvider, { llm_id: res.data.id });
          }
        }
      }

      // 保存 Embedding 模型配置
      const embOptions = (providerDiscoveredModels[selectedProvider] || []).filter(m => m.model_type === 'embedding').map(m => m.name);
      const embModel = cfg.embedding_model || embOptions[0] || '';
      if (embModel) {
        const embPayload = {
          ...basePayload,
          model_name: embModel,
          model_type: 'embedding' as ModelType,
          use_case: 'embedding',
          temperature: 0,
          max_tokens: 8192,
        };
        if (cfg.embedding_id) {
          await settingsApi.updateModelConfig(cfg.embedding_id, embPayload);
        } else {
          const res = await settingsApi.createModelConfig(embPayload);
          if (res.success && res.data) {
            updateConfig(selectedProvider, { embedding_id: res.data.id });
          }
        }
      }

      // 保存 Rerank 模型配置
      const rerankOptions = (providerDiscoveredModels[selectedProvider] || []).filter(m => m.model_type === 'rerank').map(m => m.name);
      const rerankModel = cfg.rerank_model || rerankOptions[0] || '';
      if (rerankModel) {
        const rerankPayload = {
          ...basePayload,
          model_name: rerankModel,
          model_type: 'rerank' as ModelType,
          use_case: 'rerank',
          temperature: 0,
          max_tokens: 0,
        };
        if (cfg.rerank_id) {
          await settingsApi.updateModelConfig(cfg.rerank_id, rerankPayload);
        } else {
          const res = await settingsApi.createModelConfig(rerankPayload);
          if (res.success && res.data) {
            updateConfig(selectedProvider, { rerank_id: res.data.id });
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

  if (loading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-16">
          <Spin size="large" tip="加载模型配置..." />
        </div>
      </Card>
    );
  }

  const currentCatalog = selectedProvider ? PLATFORM_CATALOG[selectedProvider] : null;
  const currentConfig = selectedProvider ? getConfig(selectedProvider) : null;

  // 只从已发现模型中取选项（不使用静态目录）
  const getModelOptions = (type: 'llm' | 'embedding' | 'rerank'): string[] => {
    if (!selectedProvider) return [];
    return (providerDiscoveredModels[selectedProvider] || [])
      .filter(m => m.model_type === type)
      .map(m => m.name);
  };

  return (
    <div className="space-y-4">
      {/* 平台选择 */}
      <Card>
        <Title level={5} className="mb-1">选择模型平台</Title>
        <Paragraph type="secondary" className="mb-4">
          选择您的 AI 服务提供商，然后配置对应的模型和 API Key。
        </Paragraph>
        <Row gutter={[12, 12]}>
          {Object.entries(PLATFORM_CATALOG).map(([provider, info]) => {
            const isSelected = selectedProvider === provider;
            const hasConfig = !!configs[provider]?.api_key;
            const discovered = providerDiscoveredModels[provider] || [];
            const supportedTypes: ModelType[] = [];
            if (discovered.some(m => m.model_type === 'llm')) supportedTypes.push('llm');
            if (discovered.some(m => m.model_type === 'embedding')) supportedTypes.push('embedding');
            if (discovered.some(m => m.model_type === 'rerank')) supportedTypes.push('rerank');

            return (
              <Col key={provider} xs={12} sm={8} md={6}>
                <Card
                  hoverable
                  size="small"
                  onClick={() => handleSelectProvider(provider)}
                  style={{
                    border: isSelected ? '2px solid #1677ff' : '1px solid #d9d9d9',
                    background: isSelected ? '#f0f5ff' : undefined,
                    cursor: 'pointer',
                    minHeight: 110,
                  }}
                  bodyStyle={{ padding: '12px' }}
                >
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center justify-between">
                      <Text strong style={{ fontSize: 14 }}>{info.name}</Text>
                      {hasConfig && (
                        <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />
                      )}
                    </div>
                    <Text type="secondary" style={{ fontSize: 11 }}>{info.description}</Text>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {supportedTypes.map(t => (
                        <Tag
                          key={t}
                          color={t === 'llm' ? 'blue' : t === 'embedding' ? 'green' : 'orange'}
                          style={{ fontSize: 10, padding: '0 4px', margin: 0 }}
                        >
                          {MODEL_TYPE_LABELS[t]}
                        </Tag>
                      ))}
                    </div>
                  </div>
                </Card>
              </Col>
            );
          })}
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
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSave}
            >
              保存配置
            </Button>
          }
        >
          {/* API Key */}
          <div className="mb-4">
            <Text strong className="block mb-1">
              API Key{' '}
              {selectedProvider === 'private'
                ? <Text type="secondary">（可选）</Text>
                : <Text type="danger">*</Text>
              }
            </Text>
            <Space.Compact style={{ width: '100%' }}>
              <Input.Password
                value={currentConfig.api_key}
                onChange={e => {
                  updateConfig(selectedProvider, { api_key: e.target.value });
                  setValidationStatus('idle');
                  setValidationMsg('');
                }}
                placeholder="输入 API Key..."
                style={{ flex: 1 }}
              />
              <Button
                onClick={handleValidate}
                loading={validationStatus === 'validating'}
                icon={
                  validationStatus === 'valid' ? (
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  ) : validationStatus === 'invalid' ? (
                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                  ) : validationStatus === 'validating' ? (
                    <LoadingOutlined />
                  ) : undefined
                }
              >
                {validationStatus === 'validating' ? '验证中' : '验证'}
              </Button>
            </Space.Compact>

            {validationStatus === 'valid' && (
              <Alert
                className="mt-2"
                type="success"
                message={validationMsg}
                showIcon
                banner
              />
            )}
            {validationStatus === 'invalid' && (
              <Alert
                className="mt-2"
                type="error"
                message={validationMsg}
                showIcon
                banner
              />
            )}

            {/* 自动发现模型（仅支持特定 provider） */}
            {validationStatus === 'valid' && selectedProvider && DISCOVER_CAPABLE_PROVIDERS.has(selectedProvider) && (
              <div className="mt-3">
                <Button
                  icon={<SearchOutlined />}
                  loading={discovering}
                  onClick={handleDiscover}
                >
                  {discovering ? '检测中...' : '检测可用模型'}
                </Button>
              </div>
            )}
          </div>

          {/* 已发现的模型列表 */}
          {discoveredModels.length > 0 && (() => {
            const llmModels = discoveredModels.filter(m => m.model_type === 'llm');
            const embModels = discoveredModels.filter(m => m.model_type === 'embedding');
            const rerankModels = discoveredModels.filter(m => m.model_type === 'rerank');
            return (
              <div className="mb-4 p-3 rounded" style={{ background: '#f8f9fa', border: '1px solid #e8e8e8' }}>
                <div className="flex items-center justify-between mb-3">
                  <Text strong>检测到以下可用模型</Text>
                  <Button
                    type="primary"
                    size="small"
                    icon={<ThunderboltOutlined />}
                    loading={batchSaving}
                    onClick={handleBatchSave}
                  >
                    一键保存全部模型
                  </Button>
                </div>
                {llmModels.length > 0 && (
                  <div className="mb-2">
                    <Tag color="blue">大语言模型</Tag>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {llmModels.map(m => (
                        <Tag key={m.name} style={{ fontSize: 11 }}>{m.name}</Tag>
                      ))}
                    </div>
                  </div>
                )}
                {embModels.length > 0 && (
                  <div className="mb-2">
                    <Tag color="green">嵌入模型</Tag>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {embModels.map(m => (
                        <Tag key={m.name} style={{ fontSize: 11 }}>{m.name}</Tag>
                      ))}
                    </div>
                  </div>
                )}
                {rerankModels.length > 0 && (
                  <div className="mb-2">
                    <Tag color="orange">重排模型</Tag>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {rerankModels.map(m => (
                        <Tag key={m.name} style={{ fontSize: 11 }}>{m.name}</Tag>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}

          {/* 自定义 API Base（私有部署必填，其他平台可折叠） */}
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
              items={[
                {
                  key: 'apibase',
                  label: <Text type="secondary" style={{ fontSize: 13 }}>自定义 API Base URL（可选，用于代理或兼容接口）</Text>,
                  children: (
                    <Input
                      value={currentConfig.api_base}
                      onChange={e => updateConfig(selectedProvider, { api_base: e.target.value })}
                      placeholder="例如：https://your-proxy.com/v1"
                    />
                  ),
                },
              ]}
            />
          ) : null}

          <Divider style={{ margin: '12px 0' }} />

          {/* 大语言模型 */}
          {(() => {
            const llmOptions = getModelOptions('llm');
            return llmOptions.length > 0 ? (
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-1">
                  <Tag color="blue">大语言模型</Tag>
                  <Text type="secondary" style={{ fontSize: 12 }}>用于对话和文本生成</Text>
                </div>
                <Select
                  value={currentConfig.llm_model || llmOptions[0]}
                  onChange={v => updateConfig(selectedProvider, { llm_model: v })}
                  style={{ width: '100%' }}
                >
                  {llmOptions.map(m => (
                    <Option key={m} value={m}>{m}</Option>
                  ))}
                </Select>
              </div>
            ) : null;
          })()}

          {/* 嵌入模型 */}
          {(() => {
            const embOptions = getModelOptions('embedding');
            return embOptions.length > 0 ? (
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-1">
                  <Tag color="green">嵌入模型</Tag>
                  <Text type="secondary" style={{ fontSize: 12 }}>用于知识库向量化检索</Text>
                </div>
                <Select
                  value={currentConfig.embedding_model || embOptions[0]}
                  onChange={v => updateConfig(selectedProvider, { embedding_model: v })}
                  style={{ width: '100%' }}
                >
                  {embOptions.map(m => (
                    <Option key={m} value={m}>{m}</Option>
                  ))}
                </Select>
              </div>
            ) : (
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-1">
                  <Tag color="default">嵌入模型</Tag>
                </div>
                <Text type="secondary" style={{ fontSize: 12 }}>当前平台不提供嵌入模型</Text>
              </div>
            );
          })()}

          {/* 重排模型 */}
          {(() => {
            const rerankOptions = getModelOptions('rerank');
            return rerankOptions.length > 0 ? (
              <div className="mb-2">
                <div className="flex items-center gap-2 mb-1">
                  <Tag color="orange">重排模型</Tag>
                  <Text type="secondary" style={{ fontSize: 12 }}>用于 RAG 检索结果重新排序</Text>
                </div>
                <Select
                  value={currentConfig.rerank_model || rerankOptions[0]}
                  onChange={v => updateConfig(selectedProvider, { rerank_model: v })}
                  style={{ width: '100%' }}
                >
                  {rerankOptions.map(m => (
                    <Option key={m} value={m}>{m}</Option>
                  ))}
                </Select>
              </div>
            ) : (
              <div className="mb-2">
                <div className="flex items-center gap-2 mb-1">
                  <Tag color="default">重排模型</Tag>
                </div>
                <Text type="secondary" style={{ fontSize: 12 }}>当前平台不提供重排模型</Text>
              </div>
            );
          })()}
        </Card>
      )}
    </div>
  );
}

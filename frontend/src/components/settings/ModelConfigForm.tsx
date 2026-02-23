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
} from '@ant-design/icons';
import { settingsApi } from '@/lib/api/settings';
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
    llm: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    embedding: ['text-embedding-3-small', 'text-embedding-3-large', 'text-embedding-ada-002'],
    rerank: [],
    needsApiBase: true,
  },
  anthropic: {
    name: 'Anthropic',
    description: 'Claude 3.5 Sonnet / Haiku 等',
    llm: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229', 'claude-3-haiku-20240307'],
    embedding: [],
    rerank: [],
  },
  deepseek: {
    name: 'DeepSeek',
    description: 'DeepSeek-Chat / Reasoner',
    llm: ['deepseek-chat', 'deepseek-reasoner'],
    embedding: [],
    rerank: [],
    needsApiBase: true,
  },
  zhipuai: {
    name: '智谱 AI',
    description: 'GLM-4 系列',
    llm: ['glm-4-plus', 'glm-4', 'glm-4-flash', 'glm-3-turbo'],
    embedding: ['embedding-3'],
    rerank: [],
  },
  moonshot: {
    name: 'Moonshot (Kimi)',
    description: 'Moonshot-v1 系列',
    llm: ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
    embedding: [],
    rerank: [],
  },
  qwen: {
    name: '通义千问',
    description: 'Qwen-Max / Plus / Turbo',
    llm: ['qwen-max', 'qwen-plus', 'qwen-turbo'],
    embedding: ['text-embedding-v3', 'text-embedding-v2'],
    rerank: [],
    needsApiBase: true,
  },
  cohere: {
    name: 'Cohere',
    description: 'Command-R + Rerank',
    llm: ['command-r-plus', 'command-r'],
    embedding: ['embed-multilingual-v3.0', 'embed-english-v3.0'],
    rerank: ['rerank-v3.5', 'rerank-multilingual-v3.0'],
  },
  jina: {
    name: 'Jina AI',
    description: '嵌入 & 重排模型',
    llm: [],
    embedding: ['jina-embeddings-v3', 'jina-embeddings-v2-base-zh'],
    rerank: ['jina-reranker-v2-base-multilingual', 'jina-reranker-v1-base-en'],
  },
};

const MODEL_TYPE_LABELS: Record<ModelType, string> = {
  llm: '大语言模型',
  embedding: '嵌入模型',
  rerank: '重排模型',
};

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

  // 初始化：从后端加载已有配置
  useEffect(() => {
    const load = async () => {
      setLoading(true);
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

          // 自动展开第一个已有配置的平台
          const firstConfigured = Object.keys(merged)[0];
          if (firstConfigured) setSelectedProvider(firstConfigured);
        }
      } catch {
        message.error('加载模型配置失败');
      } finally {
        setLoading(false);
      }
    };
    load();
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
  };

  // 验证 API Key
  const handleValidate = async () => {
    if (!selectedProvider) return;
    const cfg = getConfig(selectedProvider);
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
    const catalog = PLATFORM_CATALOG[selectedProvider];

    if (!cfg.api_key.trim()) {
      message.warning('请输入 API Key');
      return;
    }

    // 必须先验证或已验证有效
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
      if (catalog.llm.length > 0 && cfg.llm_model) {
        const llmPayload = {
          ...basePayload,
          model_name: cfg.llm_model,
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
      if (catalog.embedding.length > 0 && cfg.embedding_model) {
        const embPayload = {
          ...basePayload,
          model_name: cfg.embedding_model,
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
      if (catalog.rerank.length > 0 && cfg.rerank_model) {
        const rerankPayload = {
          ...basePayload,
          model_name: cfg.rerank_model,
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
            const supportedTypes: ModelType[] = [];
            if (info.llm.length > 0) supportedTypes.push('llm');
            if (info.embedding.length > 0) supportedTypes.push('embedding');
            if (info.rerank.length > 0) supportedTypes.push('rerank');

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
              API Key <Text type="danger">*</Text>
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
          </div>

          {/* 自定义 API Base（可折叠） */}
          {currentCatalog.needsApiBase && (
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
          )}

          <Divider style={{ margin: '12px 0' }} />

          {/* 大语言模型 */}
          {currentCatalog.llm.length > 0 && (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-1">
                <Tag color="blue">大语言模型</Tag>
                <Text type="secondary" style={{ fontSize: 12 }}>用于对话和文本生成</Text>
              </div>
              <Select
                value={currentConfig.llm_model || currentCatalog.llm[0]}
                onChange={v => updateConfig(selectedProvider, { llm_model: v })}
                style={{ width: '100%' }}
              >
                {currentCatalog.llm.map(m => (
                  <Option key={m} value={m}>{m}</Option>
                ))}
              </Select>
            </div>
          )}

          {/* 嵌入模型 */}
          {currentCatalog.embedding.length > 0 ? (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-1">
                <Tag color="green">嵌入模型</Tag>
                <Text type="secondary" style={{ fontSize: 12 }}>用于知识库向量化检索</Text>
              </div>
              <Select
                value={currentConfig.embedding_model || currentCatalog.embedding[0]}
                onChange={v => updateConfig(selectedProvider, { embedding_model: v })}
                style={{ width: '100%' }}
              >
                {currentCatalog.embedding.map(m => (
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
          )}

          {/* 重排模型 */}
          {currentCatalog.rerank.length > 0 ? (
            <div className="mb-2">
              <div className="flex items-center gap-2 mb-1">
                <Tag color="orange">重排模型</Tag>
                <Text type="secondary" style={{ fontSize: 12 }}>用于 RAG 检索结果重新排序</Text>
              </div>
              <Select
                value={currentConfig.rerank_model || currentCatalog.rerank[0]}
                onChange={v => updateConfig(selectedProvider, { rerank_model: v })}
                style={{ width: '100%' }}
              >
                {currentCatalog.rerank.map(m => (
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
          )}
        </Card>
      )}
    </div>
  );
}

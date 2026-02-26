'use client';

import { useEffect, useState } from 'react';
import { Select, Input, Switch, Slider, Space, Typography, Alert, Card } from 'antd';
import { settingsApi, ModelConfig } from '@/lib/api/settings';

const { TextArea } = Input;
const { Text } = Typography;

export interface PlaygroundSettings {
  modelConfigId: number | null;
  systemPrompt: string;
  useRag: boolean;
  ragTopK: number;
}

interface PlaygroundConfigProps {
  value: PlaygroundSettings;
  onChange: (settings: PlaygroundSettings) => void;
}

export default function PlaygroundConfig({ value, onChange }: PlaygroundConfigProps) {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [noModels, setNoModels] = useState(false);

  useEffect(() => {
    loadModels();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const loadModels = async () => {
    setLoading(true);
    try {
      const res = await settingsApi.getModelConfigs();
      if (res.success && res.data) {
        const llmModels = res.data.filter(
          (m) => m.model_type === 'llm' && m.is_active
        );
        setModels(llmModels);
        if (llmModels.length === 0) {
          setNoModels(true);
          return;
        }
        const defaultModel = llmModels.find((m) => m.is_default) || llmModels[0];
        if (!value.modelConfigId) {
          onChange({ ...value, modelConfigId: defaultModel.id });
        }
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  if (noModels) {
    return (
      <Alert
        type="warning"
        message="尚未配置模型"
        description="请前往「系统设置 > 模型配置」添加 LLM 模型后再使用 Playground。"
        showIcon
      />
    );
  }

  return (
    <Card size="small" className="mb-4">
      <Space direction="vertical" className="w-full" size="middle">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Text strong className="whitespace-nowrap">模型</Text>
            <Select
              loading={loading}
              value={value.modelConfigId}
              onChange={(id) => onChange({ ...value, modelConfigId: id })}
              style={{ minWidth: 220 }}
              placeholder="选择模型"
              options={models.map((m) => ({
                value: m.id,
                label: `${m.model_name} (${m.provider})`,
              }))}
            />
          </div>

          <div className="flex items-center gap-2">
            <Text strong className="whitespace-nowrap">RAG</Text>
            <Switch
              checked={value.useRag}
              onChange={(checked) => onChange({ ...value, useRag: checked })}
              size="small"
            />
          </div>

          {value.useRag && (
            <div className="flex items-center gap-2 min-w-[160px]">
              <Text className="whitespace-nowrap text-xs text-gray-500">Top-K</Text>
              <Slider
                min={1}
                max={10}
                value={value.ragTopK}
                onChange={(v) => onChange({ ...value, ragTopK: v })}
                style={{ width: 100 }}
              />
              <Text className="text-xs">{value.ragTopK}</Text>
            </div>
          )}
        </div>

        <div>
          <Text className="text-xs text-gray-500 mb-1 block">系统提示词（可选）</Text>
          <TextArea
            value={value.systemPrompt}
            onChange={(e) => onChange({ ...value, systemPrompt: e.target.value })}
            placeholder="自定义系统提示词，留空使用默认"
            autoSize={{ minRows: 1, maxRows: 4 }}
          />
        </div>
      </Space>
    </Card>
  );
}

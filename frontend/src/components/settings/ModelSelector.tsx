'use client';

import { memo } from 'react';
import { Select, Tag, Typography } from 'antd';
import { ModelType } from '@/types';
import { MODEL_TYPE_LABELS, MODEL_TYPE_COLORS } from './ProviderCard';

const { Text } = Typography;
const { Option } = Select;

const MODEL_TYPE_DESCRIPTIONS: Record<ModelType, string> = {
  llm: '用于对话和文本生成',
  embedding: '用于知识库向量化检索',
  rerank: '用于 RAG 检索结果重新排序',
  image_generation: '用于海报和图片生成',
  video_generation: '用于视频内容生成',
};

interface ModelSelectorProps {
  modelType: ModelType;
  options: string[];
  value: string;
  onChange: (value: string) => void;
  /** 当无可用模型时是否显示提示（默认显示） */
  showEmpty?: boolean;
}

function ModelSelector({ modelType, options, value, onChange, showEmpty = false }: ModelSelectorProps) {
  if (options.length === 0) {
    if (!showEmpty) return null;
    return (
      <div className="mb-2">
        <div className="flex items-center gap-2 mb-1">
          <Tag color="default">{MODEL_TYPE_LABELS[modelType]}</Tag>
        </div>
        <Text type="secondary" style={{ fontSize: 12 }}>
          当前平台不提供{MODEL_TYPE_LABELS[modelType]}
        </Text>
      </div>
    );
  }

  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-1">
        <Tag color={MODEL_TYPE_COLORS[modelType] || 'default'}>
          {MODEL_TYPE_LABELS[modelType]}
        </Tag>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {MODEL_TYPE_DESCRIPTIONS[modelType]}
        </Text>
      </div>
      <Select
        value={value || options[0]}
        onChange={onChange}
        style={{ width: '100%' }}
      >
        {options.map(m => (
          <Option key={m} value={m}>{m}</Option>
        ))}
      </Select>
    </div>
  );
}

export default memo(ModelSelector);

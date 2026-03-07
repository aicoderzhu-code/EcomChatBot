'use client';

import { memo } from 'react';
import { Card, Tag, Typography } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';
import { ModelType } from '@/types';

const { Text } = Typography;

const MODEL_TYPE_LABELS: Record<ModelType, string> = {
  llm: '大语言模型',
  embedding: '嵌入模型',
  rerank: '重排模型',
  image_generation: '图像生成',
  video_generation: '视频生成',
};

const MODEL_TYPE_COLORS: Record<string, string> = {
  llm: 'blue',
  embedding: 'green',
  rerank: 'orange',
  image_generation: 'purple',
  video_generation: 'magenta',
};

interface ProviderCardProps {
  provider: string;
  name: string;
  description: string;
  supportedTypes: ModelType[];
  isSelected: boolean;
  hasConfig: boolean;
  onClick: () => void;
}

function ProviderCard({
  name,
  description,
  supportedTypes,
  isSelected,
  hasConfig,
  onClick,
}: ProviderCardProps) {
  return (
    <Card
      hoverable
      size="small"
      onClick={onClick}
      style={{
        border: isSelected ? '2px solid var(--primary)' : '1px solid #d9d9d9',
        background: isSelected ? 'var(--brand-50)' : undefined,
        cursor: 'pointer',
        minHeight: 110,
      }}
      styles={{ body: { padding: '12px' } }}
    >
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <Text strong style={{ fontSize: 14 }}>{name}</Text>
          {hasConfig && (
            <CheckCircleOutlined className="text-success-500 text-sm" />
          )}
        </div>
        <Text type="secondary" style={{ fontSize: 11 }}>{description}</Text>
        <div className="flex flex-wrap gap-1 mt-1">
          {supportedTypes.map(t => (
            <Tag
              key={t}
              color={MODEL_TYPE_COLORS[t] || 'default'}
              style={{ fontSize: 10, padding: '0 4px', margin: 0 }}
            >
              {MODEL_TYPE_LABELS[t]}
            </Tag>
          ))}
        </div>
      </div>
    </Card>
  );
}

export default memo(ProviderCard);
export { MODEL_TYPE_LABELS, MODEL_TYPE_COLORS };

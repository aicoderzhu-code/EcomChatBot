'use client';

import { memo } from 'react';
import { Button, Tag, Typography } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import { DiscoveredModel } from '@/lib/api/settings';

const { Text } = Typography;

interface ModelGroup {
  type: string;
  label: string;
  color: string;
}

const MODEL_GROUPS: ModelGroup[] = [
  { type: 'llm', label: '大语言模型', color: 'blue' },
  { type: 'embedding', label: '嵌入模型', color: 'green' },
  { type: 'rerank', label: '重排模型', color: 'orange' },
  { type: 'image_generation', label: '图像生成', color: 'purple' },
  { type: 'video_generation', label: '视频生成', color: 'magenta' },
];

interface DiscoveredModelsListProps {
  models: DiscoveredModel[];
  saving: boolean;
  onBatchSave: () => void;
}

function DiscoveredModelsList({ models, saving, onBatchSave }: DiscoveredModelsListProps) {
  if (models.length === 0) return null;

  return (
    <div className="mb-4 p-3 rounded bg-neutral-50 border border-neutral-200">
      <div className="flex items-center justify-between mb-3">
        <Text strong>检测到以下可用模型</Text>
        <Button
          type="primary"
          size="small"
          icon={<ThunderboltOutlined />}
          loading={saving}
          onClick={onBatchSave}
        >
          一键保存全部模型
        </Button>
      </div>
      {MODEL_GROUPS.map(({ type, label, color }) => {
        const group = models.filter(m => m.model_type === type);
        if (group.length === 0) return null;
        return (
          <div key={type} className="mb-2">
            <Tag color={color}>{label}</Tag>
            <div className="flex flex-wrap gap-1 mt-1">
              {group.map(m => (
                <Tag key={m.name} style={{ fontSize: 11 }}>{m.name}</Tag>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default memo(DiscoveredModelsList);

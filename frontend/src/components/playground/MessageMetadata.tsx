'use client';

import { Tag, Typography, Space } from 'antd';
import {
  ClockCircleOutlined,
  DatabaseOutlined,
  RobotOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

export interface MessageMeta {
  model?: string;
  provider?: string;
  inputTokens?: number;
  outputTokens?: number;
  responseTimeMs?: number;
  ragSources?: { title: string; score: number; chunk_preview: string }[];
}

interface MessageMetadataProps {
  meta: MessageMeta;
}

export default function MessageMetadata({ meta }: MessageMetadataProps) {
  return (
    <div className="mt-2 p-3 rounded-lg bg-gray-50 border border-gray-100 text-xs">
      <Space wrap size={[12, 4]}>
        {meta.model && (
          <span className="flex items-center gap-1">
            <RobotOutlined className="text-gray-400" />
            <Text className="text-gray-600">{meta.model}</Text>
          </span>
        )}
        {(meta.inputTokens !== undefined || meta.outputTokens !== undefined) && (
          <span className="flex items-center gap-1">
            <DatabaseOutlined className="text-gray-400" />
            <Text className="text-gray-600">
              输入 {meta.inputTokens ?? 0} | 输出 {meta.outputTokens ?? 0}
            </Text>
          </span>
        )}
        {meta.responseTimeMs !== undefined && (
          <span className="flex items-center gap-1">
            <ClockCircleOutlined className="text-gray-400" />
            <Text className="text-gray-600">{(meta.responseTimeMs / 1000).toFixed(1)}s</Text>
          </span>
        )}
      </Space>
      {meta.ragSources && meta.ragSources.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <Text className="text-gray-500 block mb-1">RAG 来源:</Text>
          <Space wrap size={4}>
            {meta.ragSources.map((s, i) => (
              <Tag key={i} color="blue" className="text-xs">
                {s.title} ({(s.score * 100).toFixed(0)}%)
              </Tag>
            ))}
          </Space>
        </div>
      )}
    </div>
  );
}

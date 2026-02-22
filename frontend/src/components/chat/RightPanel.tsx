'use client';

import { Typography, Divider, Tag } from 'antd';
import { UserOutlined, BookOutlined } from '@ant-design/icons';
import { User, KnowledgeSearchResult } from '@/types';

const { Text } = Typography;

interface RightPanelProps {
  user: User | null;
  ragSources: KnowledgeSearchResult[];
}

export default function RightPanel({ user, ragSources }: RightPanelProps) {
  return (
    <div className="w-80 bg-white border-l border-gray-200 overflow-y-auto">
      <div className="p-5">
        {/* User Profile */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-100">
            <UserOutlined className="text-gray-500" />
            <Text strong>用户画像</Text>
          </div>
          {user ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <Text type="secondary">ID:</Text>
                <Text>{user.user_external_id.slice(-4)}</Text>
              </div>
              <div className="flex justify-between">
                <Text type="secondary">等级:</Text>
                <Text>{user.level || '普通会员'}</Text>
              </div>
              <div className="flex justify-between">
                <Text type="secondary">地区:</Text>
                <Text>{user.region || '未知'}</Text>
              </div>
              {user.tags && user.tags.length > 0 && (
                <div>
                  <Text type="secondary">标签:</Text>
                  <div className="mt-1">
                    {user.tags.map((tag) => (
                      <Tag key={tag} className="mb-1">
                        {tag}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <Text type="secondary" className="text-sm">
              暂无用户信息
            </Text>
          )}
        </div>

        <Divider className="my-4" />

        {/* RAG Sources */}
        <div>
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-100">
            <BookOutlined className="text-gray-500" />
            <Text strong>知识库引用 (RAG)</Text>
          </div>
          {ragSources.length > 0 ? (
            <div className="space-y-3">
              {ragSources.map((source, index) => (
                <div
                  key={source.knowledge_id || index}
                  className="p-3 bg-sky-50 border border-sky-200 rounded-lg"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Text strong className="text-sky-700 text-sm">
                      {source.title}
                    </Text>
                  </div>
                  <Text
                    type="secondary"
                    className="text-xs line-clamp-3 block"
                  >
                    {source.content}
                  </Text>
                  <div className="mt-2 text-right">
                    <Text className="text-sky-600 text-xs">
                      匹配度: {Math.round(source.score * 100)}%
                    </Text>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Text type="secondary" className="text-sm">
              暂无知识库引用
            </Text>
          )}
        </div>
      </div>
    </div>
  );
}

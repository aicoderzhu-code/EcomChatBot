'use client';

import { useState } from 'react';
import { Card, Input, Button, Typography, Spin, Empty, Select, Form } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { KnowledgeSearchResult } from '@/types';

const { Title, Text } = Typography;

interface RerankModel {
  id: number;
  model_name: string;
  provider: string;
}

interface RetrievalTestProps {
  onSearch: (query: string, useRerank?: boolean) => Promise<KnowledgeSearchResult[]>;
  rerankModels?: RerankModel[];
}

export default function RetrievalTest({ onSearch, rerankModels }: RetrievalTestProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<KnowledgeSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [useRerank, setUseRerank] = useState<boolean>(false);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setSearched(true);
    try {
      const data = await onSearch(query, useRerank);
      setResults(data);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const hasRerankModels = rerankModels && rerankModels.length > 0;

  return (
    <Card>
      <Title level={5} className="mb-4">
        检索效果测试
      </Title>

      <div className="mb-4">
        <Text type="secondary" className="block mb-2">
          测试问题
        </Text>
        <div className="flex gap-3">
          <Input
            placeholder="输入问题测试知识库检索效果..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1"
          />
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleSearch}
            loading={loading}
          >
            测试检索
          </Button>
        </div>
      </div>

      {hasRerankModels && (
        <Form layout="inline" className="mb-4">
          <Form.Item label="重排模型（可选）">
            <Select
              style={{ width: 240 }}
              placeholder="不使用重排序"
              allowClear
              value={useRerank ? true : undefined}
              onChange={(val) => setUseRerank(!!val)}
              options={[{ value: true, label: `使用重排（已配置 ${rerankModels!.length} 个模型）` }]}
            />
          </Form.Item>
        </Form>
      )}

      {loading && (
        <div className="flex items-center justify-center py-8">
          <Spin tip="检索中..." />
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <Empty description="未找到匹配的知识" />
      )}

      {!loading && results.length > 0 && (
        <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
          <Text strong className="block mb-3">
            Top {results.length} 匹配结果{useRerank ? '（已重排序）' : ''}:
          </Text>
          <div className="space-y-3">
            {results.map((result, index) => (
              <div
                key={result.knowledge_id || index}
                className={`pb-3 ${
                  index < results.length - 1
                    ? 'border-b border-dashed border-gray-300'
                    : ''
                }`}
              >
                <div className="flex justify-between items-center mb-2">
                  <Text strong className="text-blue-600">
                    {result.title}
                  </Text>
                  <Text className="text-green-600">
                    Score: {result.score.toFixed(2)}
                  </Text>
                </div>
                <Text type="secondary" className="text-sm">
                  {result.content}
                </Text>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

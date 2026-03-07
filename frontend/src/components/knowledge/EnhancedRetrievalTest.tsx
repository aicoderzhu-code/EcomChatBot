'use client';

import { useState } from 'react';
import {
  Card, Input, Button, Typography, Empty, Select, Form,
  Tabs, Slider, Collapse, Tag, Space, Descriptions,
} from 'antd';
import { SearchOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { KnowledgeSearchResult } from '@/types';
import Skeleton from '@/components/ui/Loading/Skeleton';
import apiClient from '@/lib/api/client';
import { ApiResponse } from '@/types';

const { Title, Text, Paragraph } = Typography;

interface RerankModel {
  id: number;
  model_name: string;
  provider: string;
}

interface EnhancedRetrievalTestProps {
  onSearch: (query: string, rerankModelId?: number) => Promise<KnowledgeSearchResult[]>;
  rerankModels?: RerankModel[];
}

interface RAGTestResult {
  retrieval_results: Array<{
    title?: string;
    content?: string;
    score?: number;
    knowledge_id?: string;
    category?: string;
    source?: string;
  }>;
  generated_response: string;
  model: string;
  provider: string;
  timing: {
    retrieval_ms: number;
    generation_ms: number;
    total_ms: number;
  };
  token_usage: {
    input_tokens: number;
    output_tokens: number;
  };
  rag_sources: Array<{ title: string; score: number; chunk_preview: string }>;
}

export default function EnhancedRetrievalTest({ onSearch, rerankModels }: EnhancedRetrievalTestProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<KnowledgeSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [selectedRerankModelId, setSelectedRerankModelId] = useState<number | undefined>(undefined);
  const [topK, setTopK] = useState(5);

  // End-to-end RAG test state
  const [ragQuery, setRagQuery] = useState('');
  const [ragResult, setRagResult] = useState<RAGTestResult | null>(null);
  const [ragLoading, setRagLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await onSearch(query, selectedRerankModelId);
      setResults(data);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRAGTest = async () => {
    if (!ragQuery.trim()) return;
    setRagLoading(true);
    setRagResult(null);
    try {
      const response = await apiClient.post<ApiResponse<RAGTestResult>>('/rag/test', {
        query: ragQuery,
        top_k: topK,
        use_rerank: !!selectedRerankModelId,
      });
      if (response.data.success && response.data.data) {
        setRagResult(response.data.data);
      }
    } catch (error) {
      console.error('RAG test failed:', error);
    } finally {
      setRagLoading(false);
    }
  };

  const hasRerankModels = rerankModels && rerankModels.length > 0;

  const tabItems = [
    {
      key: 'retrieval',
      label: '检索测试',
      children: (
        <div>
          <div className="mb-4">
            <Text type="secondary" className="block mb-2">测试查询</Text>
            <div className="flex gap-3">
              <Input
                placeholder="输入问题以测试知识库检索..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onPressEnter={handleSearch}
                className="flex-1"
              />
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch} loading={loading}>
                测试
              </Button>
            </div>
          </div>

          <div className="mb-4 flex gap-4 flex-wrap items-center">
            <div className="flex items-center gap-2">
              <Text className="text-xs text-gray-500">Top-K:</Text>
              <Slider min={1} max={20} value={topK} onChange={setTopK} style={{ width: 120 }} />
              <Text className="text-xs">{topK}</Text>
            </div>
            {hasRerankModels && (
              <Form layout="inline">
                <Form.Item label="重排序模型">
                  <Select
                    style={{ width: 220 }}
                    placeholder="不使用重排序"
                    allowClear
                    value={selectedRerankModelId}
                    onChange={(val) => setSelectedRerankModelId(val)}
                    options={rerankModels!.map((m) => ({ value: m.id, label: `${m.model_name} (${m.provider})` }))}
                  />
                </Form.Item>
              </Form>
            )}
          </div>

          {loading && (
            <div className="py-6 space-y-3">
              <Skeleton variant="text" width="80%" />
              <Skeleton variant="text" width="60%" />
              <Skeleton variant="text" width="70%" />
            </div>
          )}

          {!loading && searched && results.length === 0 && (
            <Empty description="未找到匹配的知识" />
          )}

          {!loading && results.length > 0 && (
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <Text strong className="block mb-3">
                前 {results.length} 条结果{selectedRerankModelId ? '（已重排序）' : ''}：
              </Text>
              <Collapse
                size="small"
                items={results.map((result, index) => ({
                  key: index,
                  label: (
                    <div className="flex justify-between items-center w-full pr-4">
                      <Text strong className="text-blue-600">{result.title}</Text>
                      <Tag color="green">得分: {result.score.toFixed(3)}</Tag>
                    </div>
                  ),
                  children: (
                    <div>
                      <Paragraph className="text-sm text-gray-600 whitespace-pre-wrap">
                        {result.content}
                      </Paragraph>
                      {result.source && (
                        <Text type="secondary" className="text-xs">来源: {result.source}</Text>
                      )}
                    </div>
                  ),
                }))}
              />
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'rag-e2e',
      label: '端到端 RAG 测试',
      children: (
        <div>
          <div className="mb-4">
            <Text type="secondary" className="block mb-2">测试查询</Text>
            <div className="flex gap-3">
              <Input
                placeholder="输入问题进行端到端 RAG 测试..."
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                onPressEnter={handleRAGTest}
                className="flex-1"
              />
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handleRAGTest}
                loading={ragLoading}
              >
                测试
              </Button>
            </div>
          </div>

          <div className="mb-4 flex gap-4 flex-wrap items-center">
            <div className="flex items-center gap-2">
              <Text className="text-xs text-gray-500">Top-K:</Text>
              <Slider min={1} max={20} value={topK} onChange={setTopK} style={{ width: 120 }} />
              <Text className="text-xs">{topK}</Text>
            </div>
          </div>

          {ragLoading && (
            <div className="py-6 space-y-3">
              <Skeleton variant="text" width="90%" />
              <Skeleton variant="text" width="75%" />
              <Skeleton variant="rectangular" height={80} className="mt-2" />
              <Skeleton variant="text" width="60%" />
            </div>
          )}

          {ragResult && !ragLoading && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Left: knowledge sources */}
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <Text strong className="block mb-3">知识来源（{ragResult.retrieval_results.length}）</Text>
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {ragResult.rag_sources.map((s, i) => (
                    <div key={i} className="p-2 bg-white rounded border border-gray-100">
                      <div className="flex justify-between items-center mb-1">
                        <Text strong className="text-sm text-blue-600">{s.title}</Text>
                        <Tag color="green" className="text-xs">
                          {(s.score * 100).toFixed(0)}%
                        </Tag>
                      </div>
                      <Text type="secondary" className="text-xs">{s.chunk_preview}</Text>
                    </div>
                  ))}
                  {ragResult.rag_sources.length === 0 && (
                    <Text type="secondary">未检索到来源。</Text>
                  )}
                </div>
              </div>

              {/* Right: AI response */}
              <div className="bg-white p-4 rounded-lg border border-gray-200">
                <Text strong className="block mb-3">AI 回答</Text>
                <Paragraph className="whitespace-pre-wrap text-sm">
                  {ragResult.generated_response}
                </Paragraph>
              </div>

              {/* Bottom: timing & token stats */}
              <div className="lg:col-span-2">
                <Descriptions bordered size="small" column={{ xs: 2, sm: 3, lg: 6 }}>
                  <Descriptions.Item label="模型">{ragResult.model}</Descriptions.Item>
                  <Descriptions.Item label="提供商">{ragResult.provider}</Descriptions.Item>
                  <Descriptions.Item label="检索">
                    <Tag color="blue">{ragResult.timing.retrieval_ms}ms</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="生成">
                    <Tag color="purple">{ragResult.timing.generation_ms}ms</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="总计">
                    <Tag color="orange">{ragResult.timing.total_ms}ms</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Token 用量">
                    <Space size={4}>
                      <Tag>输入: {ragResult.token_usage.input_tokens}</Tag>
                      <Tag>输出: {ragResult.token_usage.output_tokens}</Tag>
                    </Space>
                  </Descriptions.Item>
                </Descriptions>
              </div>
            </div>
          )}
        </div>
      ),
    },
  ];

  return (
    <Card>
      <Title level={5} className="mb-4">检索与 RAG 测试</Title>
      <Tabs items={tabItems} />
    </Card>
  );
}

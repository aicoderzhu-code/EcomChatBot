'use client';

import { useState, useEffect } from 'react';
import {
  Card, Input, Button, Typography, Spin, Empty, Select, Form,
  Tabs, Slider, Collapse, Tag, Space, Descriptions,
} from 'antd';
import { SearchOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { KnowledgeSearchResult } from '@/types';
import { settingsApi, ModelConfig } from '@/lib/api/settings';
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
  const [ragModelConfigId, setRagModelConfigId] = useState<number | undefined>(undefined);
  const [llmModels, setLlmModels] = useState<ModelConfig[]>([]);

  useEffect(() => {
    loadLLMModels();
  }, []);

  const loadLLMModels = async () => {
    try {
      const res = await settingsApi.getModelConfigs();
      if (res.success && res.data) {
        const models = res.data.filter((m) => m.model_type === 'llm' && m.is_active);
        setLlmModels(models);
        const defaultModel = models.find((m) => m.is_default) || models[0];
        if (defaultModel) setRagModelConfigId(defaultModel.id);
      }
    } catch {
      // ignore
    }
  };

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
        model_config_id: ragModelConfigId || undefined,
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
      label: 'Retrieval Test',
      children: (
        <div>
          <div className="mb-4">
            <Text type="secondary" className="block mb-2">Test Query</Text>
            <div className="flex gap-3">
              <Input
                placeholder="Input a question to test knowledge base retrieval..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onPressEnter={handleSearch}
                className="flex-1"
              />
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch} loading={loading}>
                Test
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
                <Form.Item label="Rerank Model">
                  <Select
                    style={{ width: 220 }}
                    placeholder="No reranking"
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
            <div className="flex items-center justify-center py-8">
              <Spin tip="Retrieving..." />
            </div>
          )}

          {!loading && searched && results.length === 0 && (
            <Empty description="No matching knowledge found" />
          )}

          {!loading && results.length > 0 && (
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <Text strong className="block mb-3">
                Top {results.length} results{selectedRerankModelId ? ' (reranked)' : ''}:
              </Text>
              <Collapse
                size="small"
                items={results.map((result, index) => ({
                  key: index,
                  label: (
                    <div className="flex justify-between items-center w-full pr-4">
                      <Text strong className="text-blue-600">{result.title}</Text>
                      <Tag color="green">Score: {result.score.toFixed(3)}</Tag>
                    </div>
                  ),
                  children: (
                    <div>
                      <Paragraph className="text-sm text-gray-600 whitespace-pre-wrap">
                        {result.content}
                      </Paragraph>
                      {result.source && (
                        <Text type="secondary" className="text-xs">Source: {result.source}</Text>
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
      label: 'End-to-End RAG Test',
      children: (
        <div>
          <div className="mb-4">
            <Text type="secondary" className="block mb-2">Test Query</Text>
            <div className="flex gap-3">
              <Input
                placeholder="Input a question for end-to-end RAG test..."
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
                Test
              </Button>
            </div>
          </div>

          <div className="mb-4 flex gap-4 flex-wrap items-center">
            <div className="flex items-center gap-2">
              <Text className="text-xs text-gray-500">LLM Model:</Text>
              <Select
                style={{ minWidth: 220 }}
                value={ragModelConfigId}
                onChange={setRagModelConfigId}
                placeholder="Select model"
                options={llmModels.map((m) => ({
                  value: m.id,
                  label: `${m.model_name} (${m.provider})`,
                }))}
              />
            </div>
            <div className="flex items-center gap-2">
              <Text className="text-xs text-gray-500">Top-K:</Text>
              <Slider min={1} max={20} value={topK} onChange={setTopK} style={{ width: 120 }} />
              <Text className="text-xs">{topK}</Text>
            </div>
          </div>

          {ragLoading && (
            <div className="flex items-center justify-center py-8">
              <Spin tip="Running RAG pipeline..." />
            </div>
          )}

          {ragResult && !ragLoading && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Left: knowledge sources */}
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <Text strong className="block mb-3">Knowledge Sources ({ragResult.retrieval_results.length})</Text>
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
                    <Text type="secondary">No sources retrieved.</Text>
                  )}
                </div>
              </div>

              {/* Right: AI response */}
              <div className="bg-white p-4 rounded-lg border border-gray-200">
                <Text strong className="block mb-3">AI Response</Text>
                <Paragraph className="whitespace-pre-wrap text-sm">
                  {ragResult.generated_response}
                </Paragraph>
              </div>

              {/* Bottom: timing & token stats */}
              <div className="lg:col-span-2">
                <Descriptions bordered size="small" column={{ xs: 2, sm: 3, lg: 6 }}>
                  <Descriptions.Item label="Model">{ragResult.model}</Descriptions.Item>
                  <Descriptions.Item label="Provider">{ragResult.provider}</Descriptions.Item>
                  <Descriptions.Item label="Retrieval">
                    <Tag color="blue">{ragResult.timing.retrieval_ms}ms</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Generation">
                    <Tag color="purple">{ragResult.timing.generation_ms}ms</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Total">
                    <Tag color="orange">{ragResult.timing.total_ms}ms</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Tokens">
                    <Space size={4}>
                      <Tag>In: {ragResult.token_usage.input_tokens}</Tag>
                      <Tag>Out: {ragResult.token_usage.output_tokens}</Tag>
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
      <Title level={5} className="mb-4">Retrieval & RAG Test</Title>
      <Tabs items={tabItems} />
    </Card>
  );
}

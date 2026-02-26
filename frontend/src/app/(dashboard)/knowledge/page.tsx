'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Row, Col, Card, Button, Statistic, message, Typography, Spin, Form, Select, Alert } from 'antd';
import { PlusOutlined, FileTextOutlined, AppstoreOutlined, CloudOutlined } from '@ant-design/icons';
import {
  DocumentList,
  UploadModal,
  EnhancedRetrievalTest,
} from '@/components/knowledge';
import { knowledgeApi, KnowledgeItem, KnowledgeSettings } from '@/lib/api/knowledge';
import { settingsApi, ModelConfig } from '@/lib/api/settings';
import { KnowledgeDocument, KnowledgeSearchResult } from '@/types';

const { Title } = Typography;

// Transform backend KnowledgeItem to frontend KnowledgeDocument
const transformToDocument = (item: KnowledgeItem): KnowledgeDocument => ({
  id: item.id,
  knowledge_id: item.knowledge_id,
  title: item.title,
  file_type: item.knowledge_type,
  file_size: 0, // Not provided by backend
  chunk_count: item.chunk_count,
  status: item.embedding_status === 'completed' ? 'completed' :
          item.embedding_status === 'processing' ? 'processing' :
          item.embedding_status === 'failed' ? 'failed' : 'pending',
  uploaded_at: item.created_at,
});

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [searching, setSearching] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  // Stats
  const [stats, setStats] = useState({
    totalDocuments: 0,
    totalChunks: 0,
    storageUsed: 0,
  });

  // Knowledge settings
  const [knowledgeSettings, setKnowledgeSettings] = useState<KnowledgeSettings | null>(null);
  const [modelConfigs, setModelConfigs] = useState<ModelConfig[]>([]);
  const [savingSettings, setSavingSettings] = useState(false);

  // Load stats from dedicated endpoint
  const loadStats = useCallback(async () => {
    try {
      const resp = await knowledgeApi.getStats();
      if (resp.success && resp.data) {
        setStats({
          totalDocuments: resp.data.total_documents,
          totalChunks: resp.data.total_chunks,
          storageUsed: resp.data.storage_used_mb ?? 0,
        });
      }
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }, []);

  // Polling ref
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const startPolling = useCallback((pageSize: number) => {
    stopPolling();
    pollingRef.current = setInterval(async () => {
      try {
        const resp = await knowledgeApi.list({ page: 1, size: pageSize });
        if (resp.success && resp.data) {
          const items = resp.data.items || [];
          setDocuments(items.map(transformToDocument));
          const allDone = items.every(
            (i) => i.embedding_status === 'completed' || i.embedding_status === 'failed'
          );
          if (allDone) {
            stopPolling();
          }
          await loadStats();
        }
      } catch {
        // 轮询失败静默处理，不中断轮询
      }
    }, 3000);
  }, [stopPolling, loadStats]);

  // Cleanup on unmount
  useEffect(() => () => stopPolling(), [stopPolling]);

  // Load documents
  const loadDocuments = useCallback(async (page: number, pageSize: number, keyword: string) => {
    try {
      if (keyword) setSearching(true);
      else setLoading(true);
      const response = await knowledgeApi.list({
        keyword: keyword || undefined,
        page,
        size: pageSize,
      });

      if (response.success && response.data) {
        const items = response.data.items || [];
        setDocuments(items.map(transformToDocument));
        setPagination((prev) => ({
          ...prev,
          total: response.data?.total || 0,
        }));
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
      message.error('加载文档列表失败');
    } finally {
      setLoading(false);
      setSearching(false);
    }
  }, []);

  // Load settings and model configs
  const loadSettings = useCallback(async () => {
    try {
      const [settingsResp, modelsResp] = await Promise.all([
        knowledgeApi.getSettings(),
        settingsApi.getModelConfigs(),
      ]);
      if (settingsResp.success && settingsResp.data) {
        setKnowledgeSettings(settingsResp.data);
      }
      if (modelsResp.success && modelsResp.data) {
        setModelConfigs(modelsResp.data);
      }
    } catch (err) {
      console.error('Failed to load knowledge settings:', err);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchValue);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchValue]);

  useEffect(() => {
    loadDocuments(pagination.current, pagination.pageSize, debouncedSearch);
    loadStats();
    loadSettings();
  }, [loadDocuments, loadStats, loadSettings, pagination.current, pagination.pageSize, debouncedSearch]);

  const handleSaveSettings = async () => {
    if (!knowledgeSettings) return;
    setSavingSettings(true);
    try {
      const resp = await knowledgeApi.updateSettings({
        embedding_model_id: knowledgeSettings.embedding_model_id,
        rerank_model_id: knowledgeSettings.rerank_model_id,
      });
      if (resp.success && resp.data) {
        setKnowledgeSettings(resp.data);
        message.success('设置已保存');
      } else {
        message.error('保存失败');
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : '保存失败';
      message.error(errMsg);
    } finally {
      setSavingSettings(false);
    }
  };

  const handleUpload = async (files: File[]) => {
    setUploading(true);
    try {
      for (const file of files) {
        await knowledgeApi.uploadFile(file);
      }
      message.success(`成功上传 ${files.length} 个文件`);
      setUploadModalOpen(false);
      await loadDocuments(pagination.current, pagination.pageSize, searchValue);
      await loadStats();
      startPolling(pagination.pageSize);
    } catch (err) {
      console.error('Failed to upload:', err);
      message.error('上传失败');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const response = await knowledgeApi.delete(id);
      if (response.success) {
        setDocuments((prev) => prev.filter((d) => d.knowledge_id !== id));
        message.success('删除成功');
      } else {
        message.error(response.error?.message || '删除失败');
      }
    } catch (err) {
      console.error('Failed to delete:', err);
      message.error('删除失败');
    }
  };

  const handlePreview = (doc: KnowledgeDocument) => {
    message.info(`预览: ${doc.title}`);
    // TODO: Open preview modal
  };

  const handleSearch = async (query: string, rerankModelId?: number): Promise<KnowledgeSearchResult[]> => {
    try {
      const response = await knowledgeApi.ragQuery({
        query,
        top_k: 5,
        use_rerank: !!rerankModelId,
      });
      if (response.success && response.data) {
        return response.data.results.map((item) => ({
          knowledge_id: item.knowledge_id,
          title: item.title,
          content: typeof item.content === 'string'
            ? item.content.substring(0, 200) + '...'
            : String(item.content || ''),
          score: item.score || 0.9,
          source: item.source || '',
        }));
      }
      return [];
    } catch (err) {
      console.error('Search failed:', err);
      return [];
    }
  };

  const handlePaginationChange = (page: number, pageSize: number) => {
    setPagination((prev) => ({ ...prev, current: page, pageSize }));
  };

  // Filter documents by status (client-side filtering for status)
  const filteredDocuments = documents.filter((doc) => {
    const matchesStatus = !statusFilter || doc.status === statusFilter;
    return matchesStatus;
  });

  const embeddingModels = modelConfigs.filter((m) => m.model_type === 'embedding');
  const rerankModels = modelConfigs.filter((m) => m.model_type === 'rerank');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <Title level={4} className="mb-0">知识库管理</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setUploadModalOpen(true)}
        >
          上传新文档
        </Button>
      </div>

      {/* Knowledge Settings */}
      <Card title="知识库设置" className="mb-4">
        <Form layout="inline">
          <Form.Item label="嵌入模型">
            <Select
              style={{ width: 280 }}
              placeholder="请选择嵌入模型"
              value={knowledgeSettings?.embedding_model_id ?? undefined}
              disabled={knowledgeSettings?.has_indexed_documents}
              allowClear
              options={embeddingModels.map((m) => ({
                value: m.id,
                label: `${m.model_name} (${m.provider})`,
              }))}
              onChange={(val) =>
                setKnowledgeSettings((prev) =>
                  prev ? { ...prev, embedding_model_id: val ?? null } : null
                )
              }
            />
          </Form.Item>
          <Form.Item label="重排模型（检索用）">
            <Select
              style={{ width: 280 }}
              placeholder="不使用重排序"
              value={knowledgeSettings?.rerank_model_id ?? undefined}
              allowClear
              options={rerankModels.map((m) => ({
                value: m.id,
                label: `${m.model_name} (${m.provider})`,
              }))}
              onChange={(val) =>
                setKnowledgeSettings((prev) =>
                  prev ? { ...prev, rerank_model_id: val ?? null } : null
                )
              }
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" loading={savingSettings} onClick={handleSaveSettings}>
              保存设置
            </Button>
          </Form.Item>
        </Form>
        {knowledgeSettings?.has_indexed_documents && (
          <Alert
            className="mt-3"
            message="嵌入模型已锁定"
            description="知识库已有文档。若需更换嵌入模型，请先删除所有文档。"
            type="warning"
            showIcon
          />
        )}
        <Alert
          className="mt-3"
          message="请先保存设置后再上传文档，否则刷新页面后模型选择将丢失。"
          type="info"
          showIcon
        />
      </Card>

      {/* Stats */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="总文档数"
              value={stats.totalDocuments}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="向量切片总数"
              value={stats.totalChunks}
              prefix={<AppstoreOutlined />}
              formatter={(value) => value?.toLocaleString()}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="存储占用"
              value={stats.storageUsed}
              suffix="MB"
              prefix={<CloudOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Document List */}
      <Card title="文档列表">
        {loading && !searching ? (
          <div className="flex justify-center py-12">
            <Spin size="large" />
          </div>
        ) : (
          <DocumentList
            documents={filteredDocuments}
            loading={searching}
            searchValue={searchValue}
            statusFilter={statusFilter}
            onSearchChange={setSearchValue}
            onStatusFilterChange={setStatusFilter}
            onPreview={handlePreview}
            onDelete={handleDelete}
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: pagination.total,
              onChange: handlePaginationChange,
            }}
          />
        )}
      </Card>

      {/* Enhanced Retrieval & RAG Test */}
      <EnhancedRetrievalTest
        onSearch={handleSearch}
        rerankModels={rerankModels.map((m) => ({
          id: m.id,
          model_name: m.model_name,
          provider: m.provider,
        }))}
      />

      {/* Upload Modal */}
      <UploadModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUpload={handleUpload}
        uploading={uploading}
      />
    </div>
  );
}

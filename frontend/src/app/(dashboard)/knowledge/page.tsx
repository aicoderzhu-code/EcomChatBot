'use client';

import { useState, useEffect, useCallback } from 'react';
import { Row, Col, Card, Button, Statistic, message, Typography, Spin } from 'antd';
import { PlusOutlined, FileTextOutlined, AppstoreOutlined, CloudOutlined } from '@ant-design/icons';
import {
  DocumentList,
  UploadModal,
  RetrievalTest,
} from '@/components/knowledge';
import { knowledgeApi, KnowledgeItem } from '@/lib/api/knowledge';
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

  // Load documents
  const loadDocuments = useCallback(async (page: number, pageSize: number, keyword: string) => {
    try {
      setLoading(true);
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

        // Calculate stats from loaded data
        const totalChunks = items.reduce((sum, item) => sum + item.chunk_count, 0);
        setStats({
          totalDocuments: response.data.total || 0,
          totalChunks,
          storageUsed: 0, // Not provided by API
        });
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
      message.error('加载文档列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments(pagination.current, pagination.pageSize, searchValue);
  }, [loadDocuments, pagination.current, pagination.pageSize, searchValue]);

  const handleUpload = async (files: File[]) => {
    setUploading(true);
    try {
      // For now, create knowledge entries with file content
      // In a real implementation, you would upload files to a file storage service first
      for (const file of files) {
        const content = await file.text().catch(() => `File: ${file.name}`);
        await knowledgeApi.create({
          knowledge_type: file.name.split('.').pop() || 'txt',
          title: file.name,
          content: content.substring(0, 10000), // Limit content size
          source: 'upload',
        });
      }

      message.success(`成功上传 ${files.length} 个文件`);
      setUploadModalOpen(false);
      loadDocuments(pagination.current, pagination.pageSize, searchValue); // Reload list
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

  const handleSearch = async (query: string): Promise<KnowledgeSearchResult[]> => {
    try {
      const response = await knowledgeApi.search(query, 5);
      if (response.success && response.data) {
        // Transform backend response to frontend format
        return response.data.map((item) => ({
          knowledge_id: item.knowledge_id,
          title: item.title,
          content: item.content.substring(0, 200) + '...',
          score: 0.9, // Backend doesn't provide score for simple search
          source: item.knowledge_type,
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
        {loading ? (
          <div className="flex justify-center py-12">
            <Spin size="large" />
          </div>
        ) : (
          <DocumentList
            documents={filteredDocuments}
            loading={false}
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

      {/* Retrieval Test */}
      <RetrievalTest onSearch={handleSearch} />

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

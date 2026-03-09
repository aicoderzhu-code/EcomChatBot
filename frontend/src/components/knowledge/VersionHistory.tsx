'use client';

import { useState, useCallback } from 'react';
import { Card, Timeline, Button, Modal, Tag, Descriptions, Space, message, Empty } from 'antd';
import { HistoryOutlined, RollbackOutlined, DiffOutlined } from '@ant-design/icons';
import apiClient from '@/lib/api/client';
import { ApiResponse, PaginatedResponse } from '@/types';

interface KnowledgeVersionItem {
  id: number;
  version_id: string;
  knowledge_id: string;
  version_number: number;
  title: string;
  content: string;
  category: string | null;
  change_type: string;
  change_summary: string | null;
  changed_by: string | null;
  created_at: string;
}

interface Props {
  knowledgeId: string;
  onRollback?: () => void;
}

export default function VersionHistory({ knowledgeId, onRollback }: Props) {
  const [versions, setVersions] = useState<KnowledgeVersionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<KnowledgeVersionItem | null>(null);
  const [diffOpen, setDiffOpen] = useState(false);
  const [diffData, setDiffData] = useState<Record<string, unknown> | null>(null);

  const loadVersions = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await apiClient.get<ApiResponse<PaginatedResponse<KnowledgeVersionItem>>>(
        `/knowledge/${knowledgeId}/versions`, { params: { size: 50 } },
      );
      if (resp.data.success && resp.data.data) {
        setVersions(resp.data.data.items);
      }
    } catch {
      message.error('加载版本历史失败');
    } finally {
      setLoading(false);
      setLoaded(true);
    }
  }, [knowledgeId]);

  const handleViewDetail = (version: KnowledgeVersionItem) => {
    setSelectedVersion(version);
    setDetailOpen(true);
  };

  const handleRollback = async (versionNum: number) => {
    try {
      await apiClient.post(`/knowledge/${knowledgeId}/versions/${versionNum}/rollback`);
      message.success(`已回滚到版本 v${versionNum}`);
      onRollback?.();
      loadVersions();
    } catch {
      message.error('回滚失败');
    }
  };

  const handleCompare = async (v1: number, v2: number) => {
    try {
      const resp = await apiClient.get<ApiResponse<Record<string, unknown>>>(
        `/knowledge/${knowledgeId}/versions/${v1}/diff/${v2}`,
      );
      if (resp.data.success && resp.data.data) {
        setDiffData(resp.data.data);
        setDiffOpen(true);
      }
    } catch {
      message.error('版本对比失败');
    }
  };

  const getChangeTypeTag = (type: string) => {
    switch (type) {
      case 'create': return <Tag color="green">创建</Tag>;
      case 'update': return <Tag color="blue">更新</Tag>;
      case 'rollback': return <Tag color="orange">回滚</Tag>;
      case 'delete': return <Tag color="red">删除</Tag>;
      default: return <Tag>{type}</Tag>;
    }
  };

  if (!loaded) {
    return (
      <Card size="small">
        <Button icon={<HistoryOutlined />} onClick={loadVersions} loading={loading}>
          加载版本历史
        </Button>
      </Card>
    );
  }

  if (versions.length === 0) {
    return <Empty description="暂无版本历史" />;
  }

  return (
    <div>
      <Timeline
        items={versions.map((v, idx) => ({
          color: v.change_type === 'create' ? 'green' : v.change_type === 'rollback' ? 'orange' : 'blue',
          children: (
            <div key={v.version_id}>
              <Space>
                <strong>v{v.version_number}</strong>
                {getChangeTypeTag(v.change_type)}
                <span style={{ color: '#999', fontSize: 12 }}>
                  {new Date(v.created_at).toLocaleString('zh-CN')}
                </span>
              </Space>
              {v.change_summary && <p style={{ margin: '4px 0', color: '#666' }}>{v.change_summary}</p>}
              <Space size="small" style={{ marginTop: 4 }}>
                <Button size="small" onClick={() => handleViewDetail(v)}>查看</Button>
                <Button size="small" icon={<RollbackOutlined />} onClick={() => handleRollback(v.version_number)}>
                  回滚
                </Button>
                {idx < versions.length - 1 && (
                  <Button
                    size="small"
                    icon={<DiffOutlined />}
                    onClick={() => handleCompare(versions[idx + 1].version_number, v.version_number)}
                  >
                    对比
                  </Button>
                )}
              </Space>
            </div>
          ),
        }))}
      />

      {/* 版本详情 */}
      <Modal
        title={`版本 v${selectedVersion?.version_number} 详情`}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={700}
      >
        {selectedVersion && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="标题">{selectedVersion.title}</Descriptions.Item>
            <Descriptions.Item label="分类">{selectedVersion.category || '-'}</Descriptions.Item>
            <Descriptions.Item label="内容">
              <div style={{ maxHeight: 300, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                {selectedVersion.content}
              </div>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* 版本对比 */}
      <Modal
        title="版本对比"
        open={diffOpen}
        onCancel={() => setDiffOpen(false)}
        footer={null}
        width={800}
      >
        {diffData && (
          <div>
            {(diffData as { title_changed?: boolean }).title_changed && (
              <Card size="small" title="标题变更" style={{ marginBottom: 8 }}>
                <div style={{ display: 'flex', gap: 16 }}>
                  <div style={{ flex: 1, background: '#fff1f0', padding: 8, borderRadius: 4 }}>
                    <Tag color="red">旧</Tag> {(diffData as { title_diff?: { old: string } }).title_diff?.old}
                  </div>
                  <div style={{ flex: 1, background: '#f6ffed', padding: 8, borderRadius: 4 }}>
                    <Tag color="green">新</Tag> {(diffData as { title_diff?: { new: string } }).title_diff?.new}
                  </div>
                </div>
              </Card>
            )}
            {(diffData as { content_changed?: boolean }).content_changed && (
              <Card size="small" title="内容变更">
                <div style={{ display: 'flex', gap: 16 }}>
                  <div style={{ flex: 1, background: '#fff1f0', padding: 8, borderRadius: 4, maxHeight: 300, overflow: 'auto' }}>
                    <Tag color="red">旧</Tag>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
                      {(diffData as { content_diff?: { old: string } }).content_diff?.old}
                    </pre>
                  </div>
                  <div style={{ flex: 1, background: '#f6ffed', padding: 8, borderRadius: 4, maxHeight: 300, overflow: 'auto' }}>
                    <Tag color="green">新</Tag>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
                      {(diffData as { content_diff?: { new: string } }).content_diff?.new}
                    </pre>
                  </div>
                </div>
              </Card>
            )}
            {!(diffData as { title_changed?: boolean }).title_changed && !(diffData as { content_changed?: boolean }).content_changed && (
              <Empty description="两个版本内容相同" />
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

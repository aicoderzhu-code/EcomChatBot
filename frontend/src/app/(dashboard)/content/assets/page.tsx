'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Button, Space, Tag, Image, message, Input, Modal,
  Typography, Row, Col, Spin, Empty, Tabs, Popconfirm, Switch,
} from 'antd';
import {
  AppstoreOutlined, FileImageOutlined,
  VideoCameraOutlined, FileTextOutlined,
  CloudUploadOutlined, PlayCircleOutlined,
  DeleteOutlined, DownloadOutlined, HeartOutlined, HeartFilled,
  SearchOutlined, CopyOutlined,
} from '@ant-design/icons';
import { contentApi, type GeneratedAsset } from '@/lib/api/content';
import { usePlatformUpload } from '@/hooks/usePlatformUpload';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;

export default function AssetsPage() {
  const [assets, setAssets] = useState<GeneratedAsset[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [assetType, setAssetType] = useState<string | undefined>();
  const [keyword, setKeyword] = useState('');
  const [filterSelected, setFilterSelected] = useState(false);
  const [page, setPage] = useState(1);
  const [previewAsset, setPreviewAsset] = useState<GeneratedAsset | null>(null);

  const loadAssets = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await contentApi.listAssets({
        asset_type: assetType,
        keyword: keyword || undefined,
        is_selected: filterSelected || undefined,
        page,
        size: 24,
      });
      if (resp.success && resp.data) {
        setAssets(resp.data.items);
        setTotal(resp.data.total);
      }
    } catch {
      message.error('加载素材失败');
    } finally {
      setLoading(false);
    }
  }, [assetType, keyword, filterSelected, page]);

  useEffect(() => { loadAssets(); }, [loadAssets]);

  const { uploadAsset } = usePlatformUpload(loadAssets);

  const handleDelete = async (assetId: number) => {
    try {
      const resp = await contentApi.deleteAsset(assetId);
      if (resp.success) {
        message.success('已删除');
        loadAssets();
      } else {
        message.error(resp.error?.message || '删除失败');
      }
    } catch {
      message.error('删除失败');
    }
  };

  const handleToggleSelected = async (assetId: number) => {
    try {
      const resp = await contentApi.toggleAssetSelected(assetId);
      if (resp.success) {
        setAssets(prev => prev.map(a =>
          a.id === assetId ? { ...a, is_selected: !a.is_selected } : a
        ));
      }
    } catch {
      message.error('操作失败');
    }
  };

  const handleDownload = async (asset: GeneratedAsset) => {
    if (!asset.file_url) return;
    try {
      const resp = await fetch(asset.file_url);
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ext = asset.asset_type === 'video' ? '.mp4' : '.png';
      a.download = `asset_${asset.id}${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      message.error('下载失败');
    }
  };

  const renderAssetCard = (asset: GeneratedAsset) => {
    const actions = [
      asset.asset_type !== 'text' && (
        <Button key="download" type="link" size="small" icon={<DownloadOutlined />}
          onClick={(e) => { e.stopPropagation(); handleDownload(asset); }} />
      ),
      <Button key="fav" type="link" size="small"
        icon={asset.is_selected ? <HeartFilled style={{ color: '#ff4d4f' }} /> : <HeartOutlined />}
        onClick={(e) => { e.stopPropagation(); handleToggleSelected(asset.id); }} />,
      <Button key="upload" type="link" size="small" icon={<CloudUploadOutlined />}
        disabled={!!asset.platform_url}
        onClick={(e) => { e.stopPropagation(); uploadAsset(asset.id); }}>
        {asset.platform_url ? '已上传' : '上传'}
      </Button>,
      <Popconfirm key="del" title="确定删除？" onConfirm={(e) => { e?.stopPropagation(); handleDelete(asset.id); }}>
        <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
      </Popconfirm>,
    ].filter(Boolean);

    if (asset.asset_type === 'image') {
      return (
        <Card key={asset.id} size="small" hoverable
          onClick={() => setPreviewAsset(asset)}
          cover={asset.file_url ? (
            <div style={{ height: 180, overflow: 'hidden' }}>
              <img src={asset.file_url} alt="素材" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
          ) : null}
          actions={actions}>
          <Card.Meta description={
            <Space direction="vertical" size={0}>
              <Tag color="blue"><FileImageOutlined /> 图片</Tag>
              <Text type="secondary" style={{ fontSize: 11 }}>
                {new Date(asset.created_at).toLocaleString('zh-CN')}
              </Text>
            </Space>
          } />
        </Card>
      );
    }

    if (asset.asset_type === 'video') {
      return (
        <Card key={asset.id} size="small" hoverable
          onClick={() => setPreviewAsset(asset)}
          actions={actions}>
          <div style={{ padding: '20px 0', textAlign: 'center' }}>
            <PlayCircleOutlined style={{ fontSize: 40, color: '#1677ff' }} />
          </div>
          <Card.Meta description={
            <Space direction="vertical" size={0}>
              <Tag color="purple"><VideoCameraOutlined /> 视频</Tag>
              <Text type="secondary" style={{ fontSize: 11 }}>
                {new Date(asset.created_at).toLocaleString('zh-CN')}
              </Text>
            </Space>
          } />
        </Card>
      );
    }

    // text
    return (
      <Card key={asset.id} size="small" hoverable onClick={() => setPreviewAsset(asset)} actions={actions}>
        <div style={{ minHeight: 80 }}>
          <Tag color="green"><FileTextOutlined /> 文案</Tag>
          <Text style={{ display: 'block', marginTop: 8 }}>
            {asset.content ? (asset.content.length > 100 ? asset.content.slice(0, 100) + '...' : asset.content) : '-'}
          </Text>
        </div>
        <Text type="secondary" style={{ fontSize: 11 }}>
          {new Date(asset.created_at).toLocaleString('zh-CN')}
        </Text>
      </Card>
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        <AppstoreOutlined style={{ marginRight: 8 }} />
        素材库
      </Title>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Tabs
            activeKey={assetType || 'all'}
            onChange={(key) => { setAssetType(key === 'all' ? undefined : key); setPage(1); }}
            items={[
              { key: 'all', label: '全部' },
              { key: 'image', label: '图片' },
              { key: 'video', label: '视频' },
              { key: 'text', label: '文案' },
            ]}
            style={{ marginBottom: 0 }}
          />
          <Space>
            <Space size={4}>
              <HeartFilled style={{ color: filterSelected ? '#ff4d4f' : '#d9d9d9' }} />
              <Switch size="small" checked={filterSelected}
                onChange={(v) => { setFilterSelected(v); setPage(1); }} />
            </Space>
            <Search
              placeholder="搜索文案内容"
              allowClear
              style={{ width: 200 }}
              prefix={<SearchOutlined />}
              onSearch={(v) => { setKeyword(v); setPage(1); }}
            />
          </Space>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
          </div>
        ) : assets.length === 0 ? (
          <Empty description="暂无素材" />
        ) : (
          <Row gutter={[16, 16]}>
            {assets.map((asset) => (
              <Col key={asset.id} span={6}>
                {renderAssetCard(asset)}
              </Col>
            ))}
          </Row>
        )}

        {total > 24 && (
          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Button disabled={page <= 1} onClick={() => setPage(p => p - 1)} style={{ marginRight: 8 }}>
              上一页
            </Button>
            <Text>第 {page} 页 / 共 {Math.ceil(total / 24)} 页</Text>
            <Button disabled={page * 24 >= total} onClick={() => setPage(p => p + 1)} style={{ marginLeft: 8 }}>
              下一页
            </Button>
          </div>
        )}
      </Card>

      {/* 详情预览 Modal */}
      <Modal
        open={!!previewAsset}
        onCancel={() => setPreviewAsset(null)}
        footer={null}
        width={previewAsset?.asset_type === 'text' ? 600 : 800}
        title={previewAsset?.asset_type === 'image' ? '图片预览' : previewAsset?.asset_type === 'video' ? '视频预览' : '文案详情'}
      >
        {previewAsset?.asset_type === 'image' && previewAsset.file_url && (
          <Image src={previewAsset.file_url} alt="预览" style={{ width: '100%' }} preview={false} />
        )}
        {previewAsset?.asset_type === 'video' && previewAsset.file_url && (
          <video src={previewAsset.file_url} controls style={{ width: '100%' }} />
        )}
        {previewAsset?.asset_type === 'text' && (
          <div>
            <Paragraph copyable={{ icon: [<CopyOutlined key="copy" />] }}>
              {previewAsset.content || '-'}
            </Paragraph>
          </div>
        )}
      </Modal>
    </div>
  );
}

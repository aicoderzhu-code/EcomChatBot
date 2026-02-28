'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Button, Space, Tag, Image, message,
  Typography, Row, Col, Spin, Empty, Tabs,
} from 'antd';
import {
  AppstoreOutlined, FileImageOutlined,
  VideoCameraOutlined, FileTextOutlined,
  CloudUploadOutlined, PlayCircleOutlined,
} from '@ant-design/icons';
import { contentApi, type GeneratedAsset } from '@/lib/api/content';

const { Title, Text } = Typography;

export default function AssetsPage() {
  const [assets, setAssets] = useState<GeneratedAsset[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [assetType, setAssetType] = useState<string | undefined>();
  const [page, setPage] = useState(1);

  const loadAssets = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await contentApi.listAssets({
        asset_type: assetType,
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
  }, [assetType, page]);

  useEffect(() => { loadAssets(); }, [loadAssets]);

  const handleUpload = async (assetId: number) => {
    try {
      const resp = await contentApi.uploadAssetToPlatform({
        asset_id: assetId,
        platform_config_id: 1,
      });
      if (resp.success) {
        message.success('已上传到平台');
        loadAssets();
      } else {
        message.error(resp.error?.message || '上传失败');
      }
    } catch {
      message.error('上传失败');
    }
  };

  const renderAssetCard = (asset: GeneratedAsset) => {
    if (asset.asset_type === 'image') {
      return (
        <Card
          key={asset.id}
          size="small"
          hoverable
          cover={
            asset.file_url ? (
              <Image
                src={asset.file_url}
                alt="素材图片"
                style={{ height: 180, objectFit: 'cover' }}
              />
            ) : null
          }
          actions={[
            <Button
              key="upload"
              type="link"
              size="small"
              icon={<CloudUploadOutlined />}
              disabled={!!asset.platform_url}
              onClick={() => handleUpload(asset.id)}
            >
              {asset.platform_url ? '已上传' : '上传平台'}
            </Button>,
          ]}
        >
          <Card.Meta
            description={
              <Space direction="vertical" size={0}>
                <Tag color="blue"><FileImageOutlined /> 图片</Tag>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {new Date(asset.created_at).toLocaleString('zh-CN')}
                </Text>
              </Space>
            }
          />
        </Card>
      );
    }

    if (asset.asset_type === 'video') {
      return (
        <Card
          key={asset.id}
          size="small"
          hoverable
          actions={[
            <Button
              key="upload"
              type="link"
              size="small"
              icon={<CloudUploadOutlined />}
              disabled={!!asset.platform_url}
              onClick={() => handleUpload(asset.id)}
            >
              {asset.platform_url ? '已上传' : '上传平台'}
            </Button>,
          ]}
        >
          <div style={{ padding: '20px 0', textAlign: 'center' }}>
            <PlayCircleOutlined style={{ fontSize: 40, color: '#1677ff' }} />
            {asset.file_url && (
              <div style={{ marginTop: 8 }}>
                <a href={asset.file_url} target="_blank" rel="noreferrer">查看视频</a>
              </div>
            )}
          </div>
          <Card.Meta
            description={
              <Space direction="vertical" size={0}>
                <Tag color="purple"><VideoCameraOutlined /> 视频</Tag>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {new Date(asset.created_at).toLocaleString('zh-CN')}
                </Text>
              </Space>
            }
          />
        </Card>
      );
    }

    // text type
    return (
      <Card key={asset.id} size="small" hoverable>
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
        <div style={{ marginBottom: 16 }}>
          <Tabs
            activeKey={assetType || 'all'}
            onChange={(key) => { setAssetType(key === 'all' ? undefined : key); setPage(1); }}
            items={[
              { key: 'all', label: '全部' },
              { key: 'image', label: '图片' },
              { key: 'video', label: '视频' },
              { key: 'text', label: '文案' },
            ]}
          />
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
            <Button
              disabled={page <= 1}
              onClick={() => setPage(p => p - 1)}
              style={{ marginRight: 8 }}
            >
              上一页
            </Button>
            <Text>第 {page} 页 / 共 {Math.ceil(total / 24)} 页</Text>
            <Button
              disabled={page * 24 >= total}
              onClick={() => setPage(p => p + 1)}
              style={{ marginLeft: 8 }}
            >
              下一页
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}

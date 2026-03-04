'use client';

import { Button, Card, Tag, Space, Typography, message } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, EditOutlined, DeleteOutlined, LinkOutlined } from '@ant-design/icons';
import { PlatformConfig } from '@/lib/api/platform';

const { Text } = Typography;

interface PlatformConfigCardProps {
  config: PlatformConfig;
  onEdit: () => void;
  onDelete: () => void;
  onConnect: () => void;
}

export default function PlatformConfigCard({
  config,
  onEdit,
  onDelete,
  onConnect,
}: PlatformConfigCardProps) {
  const getPlatformLabel = (platform: string): string => {
    const labels: Record<string, string> = {
      pinduoduo: '拼多多',
      douyin: '抖音抖店',
      taobao: '淘宝',
      jd: '京东',
    };
    return labels[platform] || platform;
  };

  const copyWebhookUrl = () => {
    const webhookUrl = `${window.location.origin}/api/v1/platform/${config.platform_type}/webhook`;
    navigator.clipboard.writeText(webhookUrl);
    message.success('Webhook 地址已复制');
  };

  return (
    <Card
      title={
        <Space>
          <Text strong>
            {config.shop_name || config.shop_id || '未命名店铺'}
          </Text>
          {config.is_active ? (
            <Tag icon={<CheckCircleOutlined />} color="success">
              已连接
            </Tag>
          ) : (
            <Tag icon={<CloseCircleOutlined />} color="default">
              未连接
            </Tag>
          )}
        </Space>
      }
      extra={
        <Space>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={onEdit}
          >
            编辑
          </Button>
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={onDelete}
          >
            删除
          </Button>
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Text type="secondary">平台类型：</Text>
          <Text>{getPlatformLabel(config.platform_type)}</Text>
        </div>
        <div>
          <Text type="secondary">App Key：</Text>
          <Text code>{config.app_key}</Text>
        </div>
        <div>
          <Text type="secondary">自动回复阈值：</Text>
          <Text>{config.auto_reply_threshold}</Text>
        </div>
        {config.is_active && (
          <div>
            <Text type="secondary">Webhook 地址：</Text>
            <Space>
              <Text code>{`${window.location.origin}/api/v1/platform/${config.platform_type}/webhook`}</Text>
              <Button
                type="link"
                size="small"
                icon={<LinkOutlined />}
                onClick={copyWebhookUrl}
              >
                复制
              </Button>
            </Space>
          </div>
        )}
        {!config.is_active && (
          <Button
            type="primary"
            icon={<LinkOutlined />}
            onClick={onConnect}
          >
            连接{getPlatformLabel(config.platform_type)}
          </Button>
        )}
      </Space>
    </Card>
  );
}

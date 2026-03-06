'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, Tag, Button, Table, Spin, Modal, message, Empty, Space, Typography, Tooltip } from 'antd';
import {
  LinkOutlined,
  DisconnectOutlined,
  ReloadOutlined,
  ShopOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { platformApi } from '@/lib/api/platform';
import type { PlatformApp, PlatformConfig, EcommercePlatform, AuthorizationStatus } from '@/types';

const { Text } = Typography;

const PLATFORM_INFO: Record<EcommercePlatform, { name: string; color: string }> = {
  pinduoduo: { name: '拼多多', color: '#e02e24' },
  douyin: { name: '抖音抖店', color: '#000000' },
  taobao: { name: '淘宝/天猫', color: '#ff5000' },
  jd: { name: '京东', color: '#e1251b' },
  kuaishou: { name: '快手', color: '#ff4906' },
};

const STATUS_MAP: Record<AuthorizationStatus, { text: string; color: string; icon: React.ReactNode }> = {
  authorized: { text: '已授权', color: 'success', icon: <CheckCircleOutlined /> },
  pending: { text: '待授权', color: 'default', icon: <ClockCircleOutlined /> },
  expired: { text: '已过期', color: 'error', icon: <ExclamationCircleOutlined /> },
  revoked: { text: '已断开', color: 'default', icon: <CloseCircleOutlined /> },
};

export default function PlatformManager() {
  const [apps, setApps] = useState<PlatformApp[]>([]);
  const [configs, setConfigs] = useState<PlatformConfig[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [appsData, configsData] = await Promise.all([
        platformApi.getApps(),
        platformApi.getPlatformConfigs(),
      ]);
      setApps(Array.isArray(appsData) ? appsData : []);
      setConfigs(Array.isArray(configsData) ? configsData : []);
    } catch {
      // 新 API 可能尚未部署，静默失败
      setApps([]);
      setConfigs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleConnect = (platformType: EcommercePlatform, configId?: number) => {
    const redirectUri = `${window.location.origin}/api/v1/platform/${platformType}/callback`;
    window.location.href = platformApi.getOAuthUrl(platformType, redirectUri, configId);
  };

  const handleDisconnect = (config: PlatformConfig) => {
    Modal.confirm({
      title: '确认断开连接',
      content: `确认断开与 ${config.shop_name || config.shop_id || '该店铺'} 的连接？`,
      okText: '确认',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await platformApi.disconnectPlatform(config.id);
          message.success('已断开连接');
          loadData();
        } catch {
          message.error('操作失败');
        }
      },
    });
  };

  const allPlatforms: EcommercePlatform[] = ['pinduoduo', 'douyin', 'taobao', 'jd', 'kuaishou'];
  const availablePlatforms = new Set(apps.map(a => a.platform_type));

  // 已连接的店铺表格列
  const columns = [
    {
      title: '平台',
      dataIndex: 'platform_type',
      key: 'platform_type',
      render: (val: EcommercePlatform) => (
        <Tag color={PLATFORM_INFO[val]?.color} style={{ color: '#fff' }}>
          {PLATFORM_INFO[val]?.name || val}
        </Tag>
      ),
    },
    {
      title: '店铺',
      key: 'shop',
      render: (_: unknown, record: PlatformConfig) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.shop_name || '未知店铺'}</Text>
          {record.shop_id && <Text type="secondary" style={{ fontSize: 12 }}>ID: {record.shop_id}</Text>}
        </Space>
      ),
    },
    {
      title: '授权状态',
      dataIndex: 'authorization_status',
      key: 'status',
      render: (status: AuthorizationStatus) => {
        const info = STATUS_MAP[status] || STATUS_MAP.pending;
        return <Tag icon={info.icon} color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: 'Token 过期',
      dataIndex: 'token_expires_at',
      key: 'expires',
      render: (val: string | null) => {
        if (!val) return <Text type="secondary">-</Text>;
        const date = new Date(val);
        const isExpired = date < new Date();
        return (
          <Tooltip title={date.toLocaleString()}>
            <Text type={isExpired ? 'danger' : 'secondary'}>
              {isExpired ? '已过期' : date.toLocaleDateString()}
            </Text>
          </Tooltip>
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: PlatformConfig) => (
        <Space>
          {record.authorization_status === 'authorized' ? (
            <Button
              size="small"
              danger
              icon={<DisconnectOutlined />}
              onClick={() => handleDisconnect(record)}
            >
              断开
            </Button>
          ) : (
            <Button
              size="small"
              type="primary"
              icon={<LinkOutlined />}
              onClick={() => handleConnect(record.platform_type, record.id)}
            >
              {record.authorization_status === 'expired' ? '重新授权' : '授权'}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Spin spinning={loading}>
      <div className="mb-4 flex justify-between items-center">
        <Typography.Title level={5} style={{ margin: 0 }}>平台对接管理</Typography.Title>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </div>

      {/* 平台卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
        {allPlatforms.map(pt => {
          const info = PLATFORM_INFO[pt];
          const isAvailable = availablePlatforms.has(pt);
          const platformConfigs = configs.filter(c => c.platform_type === pt);
          const hasAuthorized = platformConfigs.some(c => c.authorization_status === 'authorized');

          return (
            <Card
              key={pt}
              size="small"
              hoverable={isAvailable}
              style={{ opacity: isAvailable ? 1 : 0.5 }}
            >
              <div className="text-center">
                <ShopOutlined style={{ fontSize: 24, color: info.color }} />
                <div className="mt-2 font-medium">{info.name}</div>
                <div className="mt-2">
                  {!isAvailable ? (
                    <Tag>未配置</Tag>
                  ) : hasAuthorized ? (
                    <Tag color="success" icon={<CheckCircleOutlined />}>已连接 ({platformConfigs.filter(c => c.authorization_status === 'authorized').length})</Tag>
                  ) : (
                    <Button
                      size="small"
                      type="primary"
                      icon={<LinkOutlined />}
                      onClick={() => handleConnect(pt)}
                    >
                      连接
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* 已连接店铺列表 */}
      {configs.length > 0 ? (
        <Card title="已连接店铺" size="small">
          <Table
            dataSource={configs}
            columns={columns}
            rowKey="id"
            pagination={false}
            size="small"
          />
        </Card>
      ) : (
        <Card>
          <Empty description="暂无已连接的平台，请先连接电商平台" />
        </Card>
      )}
    </Spin>
  );
}

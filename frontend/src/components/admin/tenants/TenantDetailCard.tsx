'use client';

import { Card, Descriptions, Tag, Space, Button, Statistic, Row, Col } from 'antd';
import {
  EditOutlined,
  StopOutlined,
  CheckCircleOutlined,
  KeyOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { TenantInfo } from '@/types/admin';

interface TenantDetailCardProps {
  tenant: TenantInfo;
  onStatusChange: (status: 'active' | 'suspended') => void;
  onResetApiKey: () => void;
  onAdjustQuota: () => void;
  onAssignPlan: () => void;
}

const statusConfig: Record<string, { color: string; label: string }> = {
  active: { color: 'green', label: '正常' },
  suspended: { color: 'red', label: '已停用' },
  pending: { color: 'orange', label: '待激活' },
  deleted: { color: 'default', label: '已删除' },
};

const planConfig: Record<string, { color: string; label: string }> = {
  free: { color: 'default', label: '免费版' },
  trial: { color: 'cyan', label: '试用版' },
  monthly: { color: 'blue', label: '月付版' },
  quarterly: { color: 'geekblue', label: '季付版' },
  semi_annual: { color: 'purple', label: '半年付' },
  annual: { color: 'gold', label: '年付版' },
};

export default function TenantDetailCard({
  tenant,
  onStatusChange,
  onResetApiKey,
  onAdjustQuota,
  onAssignPlan,
}: TenantDetailCardProps) {
  const statusInfo = statusConfig[tenant.status] || { color: 'default', label: tenant.status };
  const planInfo = planConfig[tenant.current_plan] || { color: 'default', label: tenant.current_plan };

  return (
    <Card
      title="租户信息"
      extra={
        <Space>
          <Button
            icon={<SettingOutlined />}
            onClick={onAssignPlan}
          >
            套餐变更
          </Button>
          <Button
            icon={<EditOutlined />}
            onClick={onAdjustQuota}
          >
            管理订阅
          </Button>
          <Button
            icon={<KeyOutlined />}
            onClick={onResetApiKey}
          >
            重置 API Key
          </Button>
          {tenant.status === 'active' ? (
            <Button
              danger
              icon={<StopOutlined />}
              onClick={() => onStatusChange('suspended')}
            >
              停用
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => onStatusChange('active')}
            >
              启用
            </Button>
          )}
        </Space>
      }
    >
      <Descriptions column={{ xs: 1, sm: 2, md: 3 }} bordered size="small">
        <Descriptions.Item label="租户 ID">{tenant.tenant_id}</Descriptions.Item>
        <Descriptions.Item label="公司名称">{tenant.company_name}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={statusInfo.color}>{statusInfo.label}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="联系人">{tenant.contact_name || '-'}</Descriptions.Item>
        <Descriptions.Item label="联系邮箱">{tenant.contact_email}</Descriptions.Item>
        <Descriptions.Item label="联系电话">{tenant.contact_phone || '-'}</Descriptions.Item>
        <Descriptions.Item label="当前套餐">
          <Tag color={planInfo.color}>{planInfo.label}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="创建时间">
          {new Date(tenant.created_at).toLocaleString('zh-CN')}
        </Descriptions.Item>
        <Descriptions.Item label="更新时间">
          {new Date(tenant.updated_at).toLocaleString('zh-CN')}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
}

interface TenantUsageStatsProps {
  stats: {
    conversations: number;
    messages: number;
    tokens_used: number;
    storage_used: number;
  };
}

export function TenantUsageStats({ stats }: TenantUsageStatsProps) {
  return (
    <Card title="用量统计">
      <Row gutter={16}>
        <Col span={6}>
          <Statistic title="对话数" value={stats.conversations} />
        </Col>
        <Col span={6}>
          <Statistic title="消息数" value={stats.messages} />
        </Col>
        <Col span={6}>
          <Statistic title="Token 消耗" value={stats.tokens_used} />
        </Col>
        <Col span={6}>
          <Statistic title="存储使用 (MB)" value={stats.storage_used.toFixed(2)} />
        </Col>
      </Row>
    </Card>
  );
}

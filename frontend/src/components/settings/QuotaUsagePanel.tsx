'use client';

import { useEffect, useState } from 'react';
import { Card, Progress, Typography } from 'antd';
import {
  MessageOutlined,
  PictureOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';
import Skeleton from '@/components/ui/Loading/Skeleton';
import { subscriptionApi, QuotaUsage } from '@/lib/api/subscription';

const { Title, Text } = Typography;

interface QuotaItemProps {
  icon: React.ReactNode;
  label: string;
  used: number;
  quota: number;
  color: string;
}

function QuotaItem({ icon, label, used, quota, color }: QuotaItemProps) {
  const percent = quota > 0 ? Math.round((used / quota) * 100) : 0;
  const status = percent >= 100 ? 'exception' : percent >= 80 ? 'active' : 'normal';

  return (
    <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
      <div
        className="flex items-center justify-center w-10 h-10 rounded-lg text-white text-lg flex-shrink-0"
        style={{ backgroundColor: color }}
      >
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-center mb-1">
          <Text className="text-sm font-medium">{label}</Text>
          <Text className="text-xs text-gray-500">
            {used.toLocaleString()} / {quota.toLocaleString()}
          </Text>
        </div>
        <Progress
          percent={percent}
          size="small"
          status={status}
          strokeColor={percent >= 100 ? '#ff4d4f' : percent >= 80 ? '#faad14' : color}
          showInfo={false}
        />
      </div>
    </div>
  );
}

export default function QuotaUsagePanel() {
  const [loading, setLoading] = useState(true);
  const [quota, setQuota] = useState<QuotaUsage | null>(null);

  useEffect(() => {
    subscriptionApi
      .getQuotaUsage()
      .then((res) => {
        if (res.success && res.data) setQuota(res.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Card className="mb-4">
        <Skeleton variant="text" width="30%" />
        <div className="space-y-3 mt-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} variant="rectangular" height={60} />
          ))}
        </div>
      </Card>
    );
  }

  if (!quota) return null;

  return (
    <Card className="mb-4">
      <div className="flex justify-between items-center mb-4">
        <Title level={5} className="!mb-0">
          本月配额
        </Title>
        <Text type="secondary" className="text-xs">
          {quota.billing_period}
        </Text>
      </div>
      <div className="space-y-3">
        <QuotaItem
          icon={<MessageOutlined />}
          label="AI 回复"
          used={quota.reply_used}
          quota={quota.reply_quota}
          color="#1677ff"
        />
        <QuotaItem
          icon={<PictureOutlined />}
          label="图片生成"
          used={quota.image_gen_used}
          quota={quota.image_gen_quota}
          color="#722ed1"
        />
        <QuotaItem
          icon={<VideoCameraOutlined />}
          label="视频生成"
          used={quota.video_gen_used}
          quota={quota.video_gen_quota}
          color="#13c2c2"
        />
      </div>
    </Card>
  );
}

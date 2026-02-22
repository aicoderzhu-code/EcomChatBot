'use client';

import { Card, Empty, Progress, Typography } from 'antd';
import { TrendData } from '@/types/admin';

const { Text } = Typography;

interface UsageChartProps {
  data: TrendData[];
  title?: string;
  loading?: boolean;
}

export default function UsageChart({ data, title = '用量趋势', loading }: UsageChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card title={title} loading={loading}>
        <Empty description="暂无数据" />
      </Card>
    );
  }

  const maxValue = Math.max(...data.map(d => d.value));

  return (
    <Card title={title} loading={loading}>
      <div className="space-y-3">
        {data.slice(-7).map((item, index) => {
          const percentage = maxValue > 0 ? (item.value / maxValue) * 100 : 0;
          return (
            <div key={index} className="flex items-center gap-4">
              <Text className="w-20 text-sm text-gray-500">{item.date.slice(5)}</Text>
              <Progress
                percent={percentage}
                showInfo={false}
                strokeColor="#1890ff"
                className="flex-1"
              />
              <Text className="w-24 text-right text-sm">
                {item.value.toLocaleString()}
              </Text>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

interface TopTenantsUsageProps {
  tenants: Array<{ tenant_id: string; company_name: string; tokens: number }>;
  title?: string;
  loading?: boolean;
}

export function TopTenantsUsage({ tenants, title = 'Top 租户用量', loading }: TopTenantsUsageProps) {
  if (!tenants || tenants.length === 0) {
    return (
      <Card title={title} loading={loading}>
        <Empty description="暂无数据" />
      </Card>
    );
  }

  const maxTokens = tenants[0]?.tokens || 1;

  return (
    <Card title={title} loading={loading}>
      <div className="space-y-3">
        {tenants.slice(0, 10).map((tenant, index) => {
          const percentage = (tenant.tokens / maxTokens) * 100;
          return (
            <div key={tenant.tenant_id} className="flex items-center gap-4">
              <Text className="w-6 text-sm text-gray-500">{index + 1}</Text>
              <Text className="w-32 text-sm truncate" title={tenant.company_name}>
                {tenant.company_name}
              </Text>
              <Progress
                percent={percentage}
                showInfo={false}
                strokeColor="#52c41a"
                className="flex-1"
              />
              <Text className="w-24 text-right text-sm">
                {tenant.tokens.toLocaleString()}
              </Text>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

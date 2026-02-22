'use client';

import { Card, Empty } from 'antd';
import { TrendData } from '@/types/admin';

interface RevenueChartProps {
  data: TrendData[];
  title?: string;
  loading?: boolean;
}

export default function RevenueChart({ data, title = '收入趋势', loading }: RevenueChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card title={title} loading={loading}>
        <Empty description="暂无数据" />
      </Card>
    );
  }

  // Simple bar chart using CSS
  const maxValue = Math.max(...data.map(d => d.value));

  return (
    <Card title={title} loading={loading}>
      <div className="flex items-end justify-between gap-2 h-48">
        {data.map((item, index) => {
          const height = maxValue > 0 ? (item.value / maxValue) * 100 : 0;
          return (
            <div
              key={index}
              className="flex flex-col items-center flex-1"
            >
              <div className="text-xs text-gray-500 mb-1">
                ¥{item.value.toLocaleString()}
              </div>
              <div
                className="w-full bg-blue-500 rounded-t transition-all hover:bg-blue-600"
                style={{ height: `${height}%`, minHeight: height > 0 ? 4 : 0 }}
              />
              <div className="text-xs text-gray-500 mt-1 truncate w-full text-center">
                {item.date.slice(5)}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

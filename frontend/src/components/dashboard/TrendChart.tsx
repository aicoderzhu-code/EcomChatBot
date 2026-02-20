'use client';

import { Card, Typography } from 'antd';
import { Line } from '@ant-design/charts';

const { Title } = Typography;

interface TrendChartProps {
  data: { date: string; value: number }[];
  title: string;
}

export default function TrendChart({ data, title }: TrendChartProps) {
  const allZero = data.every((d) => d.value === 0);

  const config = {
    data,
    xField: 'date',
    yField: 'value',
    smooth: true,
    point: {
      size: 4,
      shape: 'circle',
    },
    color: '#2563eb',
    xAxis: {
      label: {
        autoHide: true,
        autoRotate: true,
        formatter: (v: string) => {
          const timePart = v.split(' ').pop() || v;
          return timePart.slice(0, 5);
        },
      },
      tickCount: 12,
    },
    yAxis: {
      min: 0,
      ...(allZero ? { max: 10 } : {}),
      label: {
        formatter: (v: string) => `${v}`,
      },
    },
    tooltip: {
      formatter: (datum: { date: string; value: number }) => {
        return { name: '对话数', value: datum.value };
      },
    },
  };

  return (
    <Card className="h-full">
      <Title level={5} className="mb-4">
        {title}
      </Title>
      <div style={{ height: 200 }}>
        <Line {...config} />
      </div>
    </Card>
  );
}

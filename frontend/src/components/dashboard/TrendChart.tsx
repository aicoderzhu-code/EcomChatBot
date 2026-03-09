'use client';

import { Card, Typography } from 'antd';
import { Area } from '@ant-design/charts';

const { Title } = Typography;

interface TrendChartProps {
  data: { date: string; value: number; type: string }[];
  title: string;
}

export default function TrendChart({ data, title }: TrendChartProps) {
  const allZero = data.every((d) => d.value === 0);

  const config = {
    data,
    xField: 'date',
    yField: 'value',
    seriesField: 'type',
    smooth: true,
    color: ['#2563eb', '#06b6d4'],
    areaStyle: (datum: { type: string }) => {
      if (datum.type === '对话数') {
        return {
          fill: 'l(270) 0:rgba(37,99,235,0.01) 1:rgba(37,99,235,0.25)',
        };
      }
      return {
        fill: 'l(270) 0:rgba(6,182,212,0.01) 1:rgba(6,182,212,0.25)',
      };
    },
    point: {
      size: 3,
      shape: 'circle',
    },
    xAxis: {
      label: {
        autoHide: true,
        autoRotate: false,
        formatter: (v: string) => {
          const timePart = v.split(' ').pop() || v;
          return timePart.slice(0, 5);
        },
      },
      tickCount: 8,
    },
    yAxis: {
      min: 0,
      ...(allZero ? { max: 10 } : {}),
      label: {
        formatter: (v: string) => `${v}`,
      },
    },
    tooltip: {
      shared: true,
      showCrosshairs: true,
      crosshairs: {
        type: 'x' as const,
      },
    },
    legend: {
      position: 'top-right' as const,
    },
    interactions: [{ type: 'element-highlight' }],
  };

  return (
    <Card className="h-full">
      <Title level={5} className="mb-4">
        {title}
      </Title>
      <div style={{ height: 280 }}>
        <Area {...config} />
      </div>
    </Card>
  );
}

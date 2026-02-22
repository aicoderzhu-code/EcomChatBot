'use client';

import { Card, Typography } from 'antd';
import { Pie } from '@ant-design/charts';

const { Title } = Typography;

interface IntentPieChartProps {
  data: { intent: string; count: number }[];
  title: string;
}

export default function IntentPieChart({ data, title }: IntentPieChartProps) {
  const config = {
    data,
    angleField: 'count',
    colorField: 'intent',
    radius: 0.8,
    innerRadius: 0.5,
    label: {
      type: 'outer',
      content: '{name} {percentage}',
    },
    interactions: [{ type: 'element-active' }],
    legend: {
      position: 'bottom' as const,
    },
  };

  return (
    <Card className="h-full">
      <Title level={5} className="mb-4">
        {title}
      </Title>
      <div style={{ height: 200 }}>
        <Pie {...config} />
      </div>
    </Card>
  );
}

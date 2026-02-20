'use client';

import { Card, Statistic, Typography } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  suffix?: string;
  prefix?: React.ReactNode;
}

export default function StatCard({
  title,
  value,
  change,
  suffix,
  prefix,
}: StatCardProps) {
  const getChangeDisplay = () => {
    if (change === undefined) return null;
    if (change === 0) {
      return {
        icon: <MinusOutlined />,
        colorClass: 'text-gray-500',
        text: '0% 较昨日',
      };
    }
    if (change > 0) {
      return {
        icon: <ArrowUpOutlined />,
        colorClass: 'text-green-600',
        text: `${change}% 较昨日`,
      };
    }
    return {
      icon: <ArrowDownOutlined />,
      colorClass: 'text-red-600',
      text: `${Math.abs(change)}% 较昨日`,
    };
  };

  const changeDisplay = getChangeDisplay();

  return (
    <Card className="h-full">
      <Statistic
        title={<Text type="secondary">{title}</Text>}
        value={value}
        prefix={prefix}
        valueStyle={{ fontSize: '1.75rem', fontWeight: 'bold' }}
      />
      {changeDisplay && (
        <div className="mt-2">
          <Text
            className={changeDisplay.colorClass}
            style={{ fontSize: '0.85rem' }}
          >
            {changeDisplay.icon} {changeDisplay.text}
          </Text>
        </div>
      )}
      {suffix && (
        <div className="mt-1">
          <Text type="secondary" style={{ fontSize: '0.8rem' }}>
            {suffix}
          </Text>
        </div>
      )}
    </Card>
  );
}

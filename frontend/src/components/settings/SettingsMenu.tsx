'use client';

import { Card, Menu, Typography } from 'antd';
import {
  RobotOutlined,
  KeyOutlined,
  BankOutlined,
  BellOutlined,
  ShopOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

interface SettingsMenuProps {
  selectedKey: string;
  onSelect: (key: string) => void;
}

const menuItems = [
  {
    key: 'model',
    icon: <RobotOutlined />,
    label: '模型配置',
  },
  {
    key: 'api',
    icon: <KeyOutlined />,
    label: 'API 密钥',
  },
  {
    key: 'tenant',
    icon: <BankOutlined />,
    label: '租户信息',
  },
  {
    key: 'notification',
    icon: <BellOutlined />,
    label: '通知设置',
  },
  {
    key: 'platform',
    icon: <ShopOutlined />,
    label: '平台对接',
  },
];

export default function SettingsMenu({
  selectedKey,
  onSelect,
}: SettingsMenuProps) {
  return (
    <Card className="h-full" bodyStyle={{ padding: 0 }}>
      <div className="p-4 border-b border-gray-100 bg-gray-50">
        <Text strong>设置菜单</Text>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        onClick={({ key }) => onSelect(key)}
        items={menuItems}
        style={{ borderRight: 'none' }}
      />
    </Card>
  );
}

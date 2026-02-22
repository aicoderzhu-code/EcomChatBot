'use client';

import { usePathname } from 'next/navigation';
import { Layout, Breadcrumb, Badge, Typography, Dropdown, Space } from 'antd';
import type { MenuProps } from 'antd';
import { BellOutlined, HomeOutlined, UserOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { useAdminStore } from '@/store';

const { Header: AntHeader } = Layout;
const { Text } = Typography;

const pathNames: Record<string, string> = {
  platform: '平台概览',
  tenants: '租户管理',
  overdue: '欠费租户',
  subscriptions: '订阅管理',
  payments: '支付管理',
  bills: '账单管理',
  statistics: '数据统计',
  revenue: '收入统计',
  usage: '用量分析',
  audit: '审计监控',
  security: '安全审计',
  admins: '管理员管理',
};

export default function AdminHeader() {
  const pathname = usePathname();
  const { admin } = useAdminStore();
  const pathParts = pathname.split('/').filter(Boolean);

  const breadcrumbItems = [
    {
      title: (
        <Link href="/platform">
          <HomeOutlined className="mr-1" />
          首页
        </Link>
      ),
    },
    ...pathParts.map((part, index) => {
      // Skip tenant ID parts (UUIDs)
      if (part.includes('-') && part.length > 20) {
        return {
          title: '详情',
        };
      }
      return {
        title:
          index === pathParts.length - 1 ? (
            pathNames[part] || part
          ) : (
            <Link href={`/${pathParts.slice(0, index + 1).join('/')}`}>
              {pathNames[part] || part}
            </Link>
          ),
      };
    }),
  ];

  const notificationItems: MenuProps['items'] = [
    {
      key: '1',
      label: '暂无新通知',
      disabled: true,
    },
  ];

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      label: '个人信息',
      icon: <UserOutlined />,
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      label: '退出登录',
    },
  ];

  return (
    <AntHeader
      className="bg-white flex items-center justify-between shadow-sm sticky top-0 z-10"
      style={{ padding: '0 16px', height: 64, lineHeight: '64px' }}
    >
      <Breadcrumb items={breadcrumbItems} />

      <div className="flex items-center gap-6">
        <Dropdown menu={{ items: notificationItems }} placement="bottomRight">
          <Badge count={0} size="small">
            <BellOutlined className="text-lg text-gray-600 cursor-pointer hover:text-blue-600" />
          </Badge>
        </Dropdown>

        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Space className="cursor-pointer">
            <UserOutlined className="text-gray-600" />
            <Text>{admin?.username || '管理员'}</Text>
          </Space>
        </Dropdown>
      </div>
    </AntHeader>
  );
}

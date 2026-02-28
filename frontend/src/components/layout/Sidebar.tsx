'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Menu, Avatar, Typography, Button, Tooltip } from 'antd';
import {
  DashboardOutlined,
  MessageOutlined,
  BookOutlined,
  SettingOutlined,
  LogoutOutlined,
  ShoppingCartOutlined,
  ShoppingOutlined,
  UserOutlined,
  ExperimentOutlined,
  FileImageOutlined,
  VideoCameraOutlined,
  AppstoreOutlined,
  BarChartOutlined,
  LineChartOutlined,
  FundOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '@/store';
import { settingsApi } from '@/lib/api/settings';

const { Text } = Typography;

const menuItems = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '仪表盘',
  },
  {
    key: '/chat',
    icon: <MessageOutlined />,
    label: '对话管理',
  },
  {
    key: '/knowledge',
    icon: <BookOutlined />,
    label: '知识库',
  },
  {
    key: '/products',
    icon: <ShoppingOutlined />,
    label: '商品管理',
  },
  {
    key: 'content',
    icon: <FileImageOutlined />,
    label: '内容创作',
    children: [
      { key: '/content/poster', icon: <FileImageOutlined />, label: '海报生成' },
      { key: '/content/video', icon: <VideoCameraOutlined />, label: '视频生成' },
      { key: '/content/assets', icon: <AppstoreOutlined />, label: '素材库' },
    ],
  },
  {
    key: 'analytics',
    icon: <BarChartOutlined />,
    label: '数据分析',
    children: [
      { key: '/analytics/orders', icon: <LineChartOutlined />, label: '订单分析' },
      { key: '/analytics/reports', icon: <FundOutlined />, label: '分析报告' },
      { key: '/analytics/dashboard', icon: <BarChartOutlined />, label: '销售看板' },
    ],
  },
  {
    key: '/pricing',
    icon: <DollarOutlined />,
    label: '智能定价',
  },
  {
    key: '/playground',
    icon: <ExperimentOutlined />,
    label: 'Playground',
  },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: '系统设置',
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { logout, userEmail } = useAuthStore();
  const [companyName, setCompanyName] = useState<string | null>(null);

  useEffect(() => {
    settingsApi.getTenantInfo().then((res) => {
      if (res.success && res.data) setCompanyName(res.data.company_name);
    }).catch(() => {});
  }, []);

  const handleMenuClick = ({ key }: { key: string }) => {
    router.push(key);
  };

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-[200px] z-50"
      style={{ background: '#001529' }}
    >
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-gray-700">
          <ShoppingCartOutlined className="text-2xl text-blue-400 mr-3" />
          <Text strong style={{ color: '#fff', fontSize: '1.05rem' }}>
            电商智能客服
          </Text>
        </div>

        {/* Menu */}
        <div className="flex-1 py-4 overflow-y-auto">
          <Menu
            mode="inline"
            selectedKeys={[pathname]}
            onClick={handleMenuClick}
            items={menuItems}
            theme="dark"
            style={{ background: 'transparent', borderRight: 'none' }}
          />
        </div>

        {/* User Profile */}
        <div className="p-3">
          <div
            className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl"
            style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)' }}
          >
            <Avatar
              size={36}
              style={{ background: '#1677ff', flexShrink: 0, fontWeight: 700, fontSize: '0.9rem' }}
            >
              {companyName ? companyName[0].toUpperCase() : <UserOutlined />}
            </Avatar>
            <div className="flex-1 min-w-0">
              <Text
                className="text-white block truncate"
                style={{ fontSize: '0.82rem', fontWeight: 600, lineHeight: '1.35', letterSpacing: '-0.01em' }}
              >
                {companyName || '我的平台'}
              </Text>
              <Text
                className="block truncate"
                style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', lineHeight: '1.35' }}
              >
                {userEmail || ''}
              </Text>
            </div>
            <Tooltip title="退出登录">
              <Button
                type="text"
                size="small"
                icon={<LogoutOutlined style={{ color: 'rgba(255,255,255,0.5)' }} />}
                onClick={handleLogout}
                className="hover:!bg-white/10 transition-colors flex-shrink-0"
              />
            </Tooltip>
          </div>
        </div>
      </div>
    </aside>
  );
}

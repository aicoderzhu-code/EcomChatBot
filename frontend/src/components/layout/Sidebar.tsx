'use client';

import { usePathname, useRouter } from 'next/navigation';
import { Menu, Avatar, Typography, Button, Tooltip } from 'antd';
import {
  DashboardOutlined,
  MessageOutlined,
  BookOutlined,
  SettingOutlined,
  LogoutOutlined,
  ShoppingCartOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '@/store';

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
    key: '/settings',
    icon: <SettingOutlined />,
    label: '系统设置',
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { logout, tenantId, userEmail } = useAuthStore();

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
      style={{ background: '#1f2937' }}
    >
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-gray-700">
          <ShoppingCartOutlined className="text-2xl text-white mr-3" />
          <Text strong className="text-white text-lg">
            电商智能客服
          </Text>
        </div>

        {/* Menu */}
        <div className="flex-1 py-4">
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
        <div className="p-4 border-t border-gray-700">
          <div className="flex items-center">
            <Avatar
              size={36}
              className="bg-gray-600"
              icon={<UserOutlined />}
            />
            <div className="ml-3 flex-1 min-w-0">
              <Text className="text-white text-sm block truncate">
                {userEmail || '管理员'}
              </Text>
              <Text className="text-gray-400 text-xs block truncate">
                Tenant: {tenantId?.slice(0, 8) || 'N/A'}
              </Text>
            </div>
            <Tooltip title="退出登录">
              <Button
                type="text"
                icon={<LogoutOutlined className="text-gray-400 hover:text-white" />}
                onClick={handleLogout}
              />
            </Tooltip>
          </div>
        </div>
      </div>
    </aside>
  );
}

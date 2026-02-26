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
  ExperimentOutlined,
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
      className="fixed left-0 top-0 h-screen w-[200px] z-50 flex flex-col"
      style={{ background: '#1E1B4B' }}
    >
      {/* Logo */}
      <div className="h-16 flex items-center px-5 border-b" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: '#6366F1' }}>
            <ShoppingCartOutlined className="text-white text-sm" />
          </div>
          <Text strong className="text-white" style={{ fontSize: '0.95rem', letterSpacing: '-0.01em' }}>
            电商智能客服
          </Text>
        </div>
      </div>

      {/* Menu */}
      <div className="flex-1 py-3 px-2">
        <Menu
          mode="inline"
          selectedKeys={[pathname]}
          onClick={handleMenuClick}
          items={menuItems}
          theme="dark"
          style={{
            background: 'transparent',
            borderRight: 'none',
          }}
        />
      </div>

      {/* User Profile */}
      <div className="p-3 mx-2 mb-3 rounded-xl" style={{ background: 'rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-2.5">
          <Avatar
            size={34}
            icon={<UserOutlined />}
            style={{ background: '#6366F1', flexShrink: 0 }}
          />
          <div className="flex-1 min-w-0">
            <Text className="text-white block truncate" style={{ fontSize: '0.8rem', fontWeight: 500 }}>
              {userEmail || '管理员'}
            </Text>
            <Text style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem' }} className="block truncate">
              {tenantId?.slice(0, 8) || 'N/A'}
            </Text>
          </div>
          <Tooltip title="退出登录">
            <Button
              type="text"
              size="small"
              icon={<LogoutOutlined style={{ color: 'rgba(255,255,255,0.4)' }} />}
              onClick={handleLogout}
              className="cursor-pointer hover:!bg-white/10 transition-colors"
            />
          </Tooltip>
        </div>
      </div>
    </aside>
  );
}

'use client';

import { usePathname, useRouter } from 'next/navigation';
import { Menu, Avatar, Typography, Button, Tooltip } from 'antd';
import type { MenuProps } from 'antd';
import {
  DashboardOutlined,
  TeamOutlined,
  CreditCardOutlined,
  DollarOutlined,
  BarChartOutlined,
  AuditOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useAdminStore } from '@/store';

const { Text } = Typography;

type MenuItem = Required<MenuProps>['items'][number];

const menuItems: MenuItem[] = [
  {
    key: '/platform',
    icon: <DashboardOutlined />,
    label: '平台概览',
  },
  {
    key: '/tenants',
    icon: <TeamOutlined />,
    label: '租户管理',
    children: [
      { key: '/tenants', label: '租户列表' },
      { key: '/tenants/overdue', label: '欠费租户' },
    ],
  },
  {
    key: '/subscriptions',
    icon: <CreditCardOutlined />,
    label: '订阅管理',
  },
  {
    key: '/payments',
    icon: <DollarOutlined />,
    label: '支付管理',
    children: [
      { key: '/payments', label: '支付订单' },
      { key: '/payments/bills', label: '账单管理' },
    ],
  },
  {
    key: '/statistics',
    icon: <BarChartOutlined />,
    label: '数据统计',
    children: [
      { key: '/statistics', label: '统计概览' },
      { key: '/statistics/revenue', label: '收入统计' },
      { key: '/statistics/usage', label: '用量分析' },
    ],
  },
  {
    key: '/audit',
    icon: <AuditOutlined />,
    label: '审计监控',
    children: [
      { key: '/audit', label: '操作日志' },
      { key: '/audit/security', label: '安全审计' },
    ],
  },
  {
    key: '/admins',
    icon: <UserOutlined />,
    label: '管理员管理',
  },
];

const roleLabels: Record<string, string> = {
  super_admin: '超级管理员',
  operation_admin: '运营管理员',
  support_admin: '客服管理员',
  readonly_admin: '只读管理员',
};

export default function AdminSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { logout, admin } = useAdminStore();

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    router.push(key);
  };

  const handleLogout = () => {
    logout();
    router.push('/admin-login');
  };

  // Get selected keys based on current pathname
  const getSelectedKeys = () => {
    // For nested routes, match the parent path
    if (pathname.startsWith('/tenants/overdue')) return ['/tenants/overdue'];
    if (pathname.startsWith('/tenants/')) return ['/tenants'];
    if (pathname.startsWith('/payments/bills')) return ['/payments/bills'];
    if (pathname.startsWith('/statistics/revenue')) return ['/statistics/revenue'];
    if (pathname.startsWith('/statistics/usage')) return ['/statistics/usage'];
    if (pathname.startsWith('/audit/security')) return ['/audit/security'];
    return [pathname];
  };

  // Get open keys for submenu
  const getOpenKeys = () => {
    if (pathname.startsWith('/tenants')) return ['/tenants'];
    if (pathname.startsWith('/payments')) return ['/payments'];
    if (pathname.startsWith('/statistics')) return ['/statistics'];
    if (pathname.startsWith('/audit')) return ['/audit'];
    return [];
  };

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-[200px] z-50"
      style={{ background: '#001529' }}
    >
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-gray-700">
          <SettingOutlined className="text-2xl text-blue-400 mr-3" />
          <Text strong className="text-white text-lg">
            平台管理
          </Text>
        </div>

        {/* Menu */}
        <div className="flex-1 py-4 overflow-y-auto">
          <Menu
            mode="inline"
            selectedKeys={getSelectedKeys()}
            defaultOpenKeys={getOpenKeys()}
            onClick={handleMenuClick}
            items={menuItems}
            theme="dark"
            style={{ background: 'transparent', borderRight: 'none' }}
          />
        </div>

        {/* Admin Profile */}
        <div className="p-4 border-t border-gray-700">
          <div className="flex items-center">
            <Avatar
              size={36}
              className="bg-blue-600"
              icon={<UserOutlined />}
            />
            <div className="ml-3 flex-1 min-w-0">
              <Text className="text-white text-sm block truncate">
                {admin?.username || '管理员'}
              </Text>
              <Text className="text-gray-400 text-xs block truncate">
                {admin?.role ? roleLabels[admin.role] || admin.role : ''}
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

'use client';

import { usePathname } from 'next/navigation';
import { Layout, Breadcrumb, Badge, Typography } from 'antd';
import { BellOutlined, HomeOutlined } from '@ant-design/icons';
import Link from 'next/link';

const { Header: AntHeader } = Layout;
const { Text } = Typography;

const pathNames: Record<string, string> = {
  dashboard: '仪表盘',
  chat: '对话管理',
  knowledge: '知识库',
  settings: '系统设置',
};

export default function Header() {
  const pathname = usePathname();
  const pathParts = pathname.split('/').filter(Boolean);

  const breadcrumbItems = [
    {
      title: (
        <Link href="/dashboard">
          <HomeOutlined className="mr-1" />
          首页
        </Link>
      ),
    },
    ...pathParts.map((part, index) => ({
      title:
        index === pathParts.length - 1 ? (
          pathNames[part] || part
        ) : (
          <Link href={`/${pathParts.slice(0, index + 1).join('/')}`}>
            {pathNames[part] || part}
          </Link>
        ),
    })),
  ];

  return (
    <AntHeader className="bg-white flex items-center justify-between shadow-sm sticky top-0 z-10" style={{ padding: '0 16px', height: 64, lineHeight: '64px' }}>
      <Breadcrumb items={breadcrumbItems} />

      <div className="flex items-center gap-6">
        <Badge count={0} size="small">
          <BellOutlined className="text-lg text-gray-600 cursor-pointer hover:text-blue-600" />
        </Badge>
        <div className="flex items-center gap-2">
          <Text type="secondary">API 配额:</Text>
          <Text className="text-green-600">充足</Text>
        </div>
      </div>
    </AntHeader>
  );
}

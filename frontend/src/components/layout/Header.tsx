'use client';

import { usePathname } from 'next/navigation';
import { Layout, Breadcrumb, Badge } from 'antd';
import { BellOutlined, HomeOutlined } from '@ant-design/icons';
import Link from 'next/link';

const { Header: AntHeader } = Layout;

const pathNames: Record<string, string> = {
  dashboard: '仪表盘',
  chat: '对话管理',
  knowledge: '知识库',
  settings: '系统设置',
  products: '商品管理',
  content: '内容创作',
  poster: '海报生成',
  video: '视频生成',
  prompts: '提示词管理',
  assets: '素材库',
  analytics: '数据分析',
  orders: '订单分析',
  reports: '分析报告',
  pricing: '智能定价',
  playground: 'Playground',
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
      </div>
    </AntHeader>
  );
}

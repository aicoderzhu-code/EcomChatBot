import type { Metadata } from 'next';
import { AntdRegistry } from '@ant-design/nextjs-registry';
import AntdConfigProvider from '@/components/AntdConfigProvider';
import './globals.css';

export const metadata: Metadata = {
  title: '电商智能客服平台',
  description: '基于 AI 的电商智能客服 SaaS 平台',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <AntdRegistry>
          <AntdConfigProvider>{children}</AntdConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  );
}

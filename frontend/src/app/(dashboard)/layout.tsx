'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Spin } from 'antd';
import { Sidebar, Header } from '@/components/layout';
import { useAuthStore } from '@/store';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { isAuthenticated, checkAuth } = useAuthStore();

  useEffect(() => {
    const isAuth = checkAuth();
    if (!isAuth) {
      router.push('/login');
    }
  }, [checkAuth, router]);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Sidebar />
      <div style={{ marginLeft: 200 }}>
        <Header />
        <main style={{ padding: '20px 16px', background: '#f3f4f6', minHeight: 'calc(100vh - 64px)' }}>
          {children}
        </main>
      </div>
    </div>
  );
}

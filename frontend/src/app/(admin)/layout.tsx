'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Spin } from 'antd';
import { AdminSidebar, AdminHeader } from '@/components/admin/layout';
import { useAdminStore } from '@/store';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, checkAdminAuth } = useAdminStore();

  useEffect(() => {
    // Skip auth check for login page
    if (pathname === '/admin-login') {
      return;
    }

    const isAuth = checkAdminAuth();
    if (!isAuth) {
      router.push('/admin-login');
    }
  }, [checkAdminAuth, router, pathname]);

  // Login page doesn't need the sidebar/header layout
  if (pathname === '/admin-login') {
    return <>{children}</>;
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <AdminSidebar />
      <div style={{ marginLeft: 200 }}>
        <AdminHeader />
        <main style={{ padding: '20px 16px', background: '#f3f4f6', minHeight: 'calc(100vh - 64px)' }}>
          {children}
        </main>
      </div>
    </div>
  );
}

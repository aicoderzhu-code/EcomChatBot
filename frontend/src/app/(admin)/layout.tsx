'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Spin } from 'antd';
import { AdminSidebar, AdminHeader } from '@/components/admin/layout';
import { useAdminStore } from '@/store';
import { setupApi } from '@/lib/api/admin';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, checkAdminAuth } = useAdminStore();
  const [isCheckingSetup, setIsCheckingSetup] = useState(true);

  useEffect(() => {
    const checkSetupAndAuth = async () => {
      // Skip setup check for setup page itself
      if (pathname === '/admin-setup') {
        setIsCheckingSetup(false);
        return;
      }

      try {
        // Check if system is initialized
        const statusResponse = await setupApi.getStatus();

        if (statusResponse.success && statusResponse.data) {
          // If system is not initialized, redirect to setup page
          if (!statusResponse.data.initialized) {
            router.push('/admin-setup');
            return;
          }
        }
      } catch (error) {
        // If we can't check status, continue with normal auth flow
        console.error('Failed to check setup status:', error);
      }

      setIsCheckingSetup(false);

      // Skip auth check for login page
      if (pathname === '/admin-login') {
        return;
      }

      const isAuth = checkAdminAuth();
      if (!isAuth) {
        router.push('/admin-login');
      }
    };

    checkSetupAndAuth();
  }, [checkAdminAuth, router, pathname]);

  // Setup page doesn't need the sidebar/header layout
  if (pathname === '/admin-setup') {
    return <>{children}</>;
  }

  // Login page doesn't need the sidebar/header layout
  if (pathname === '/admin-login') {
    return <>{children}</>;
  }

  // Show loading while checking setup status
  if (isCheckingSetup) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spin size="large" tip="正在检查系统状态..." />
      </div>
    );
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

'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { AdminSidebar, AdminHeader } from '@/components/admin/layout';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { useAdminStore, useUIStore } from '@/store';
import { setupApi } from '@/lib/api/admin';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, checkAdminAuth } = useAdminStore();
  const { sidebarCollapsed } = useUIStore();
  const [isCheckingSetup, setIsCheckingSetup] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

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

  const handleResize = useCallback(() => {
    setIsMobile(window.innerWidth < 768);
  }, []);

  useEffect(() => {
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [handleResize]);

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
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-brand-200 border-t-brand-500 rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-neutral-500 text-sm">正在检查系统状态...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-brand-200 border-t-brand-500 rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-neutral-500 text-sm">加载中...</p>
        </div>
      </div>
    );
  }

  const marginLeft = isMobile ? 0 : sidebarCollapsed ? 64 : 200;

  return (
    <div className="min-h-screen">
      <AdminSidebar />
      <div
        className="transition-all duration-200"
        style={{ marginLeft }}
      >
        <AdminHeader />
        <main className="animate-fade-in p-5 px-4 bg-neutral-100 min-h-[calc(100vh-64px)]">
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}

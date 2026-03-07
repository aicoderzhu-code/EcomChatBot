'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar, Header } from '@/components/layout';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { useAuthStore, useUIStore } from '@/store';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { isAuthenticated, checkAuth } = useAuthStore();
  const { sidebarCollapsed } = useUIStore();
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const isAuth = checkAuth();
    if (!isAuth) {
      router.push('/login');
    }
  }, [checkAuth, router]);

  const handleResize = useCallback(() => {
    setIsMobile(window.innerWidth < 768);
  }, []);

  useEffect(() => {
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [handleResize]);

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
      <Sidebar />
      <div
        className="transition-all duration-200"
        style={{ marginLeft }}
      >
        <Header />
        <main className="animate-fade-in p-5 px-4 bg-neutral-100 min-h-[calc(100vh-64px)]">
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}

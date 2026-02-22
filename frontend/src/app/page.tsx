'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Spin } from 'antd';
import { useAuthStore } from '@/store';

export default function HomePage() {
  const router = useRouter();
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    const isAuth = checkAuth();
    if (isAuth) {
      router.replace('/dashboard');
    } else {
      router.replace('/login');
    }
  }, [checkAuth, router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <Spin size="large" tip="加载中..." />
    </div>
  );
}

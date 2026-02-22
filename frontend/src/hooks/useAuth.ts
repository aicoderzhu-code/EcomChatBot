'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store';

export function useAuth(requireAuth = true) {
  const router = useRouter();
  const { isAuthenticated, isLoading, checkAuth, logout, tenantId } = useAuthStore();

  useEffect(() => {
    const isAuth = checkAuth();
    if (requireAuth && !isAuth && !isLoading) {
      router.push('/login');
    }
  }, [requireAuth, isLoading, checkAuth, router]);

  return {
    isAuthenticated,
    isLoading,
    logout,
    tenantId,
  };
}

export function useRequireAuth() {
  return useAuth(true);
}

export function useOptionalAuth() {
  return useAuth(false);
}

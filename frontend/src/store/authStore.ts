import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi, tokenManager } from '@/lib/api';
import { LoginRequest, RegisterRequest, Tenant } from '@/types';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  tenant: Tenant | null;
  tenantId: string | null;
  userEmail: string | null;
  error: string | null;

  login: (data: LoginRequest) => Promise<boolean>;
  register: (data: RegisterRequest) => Promise<{ success: boolean; apiKey?: string }>;
  logout: () => Promise<void>;
  checkAuth: () => boolean;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      isLoading: false,
      tenant: null,
      tenantId: null,
      userEmail: null,
      error: null,

      login: async (data: LoginRequest) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.login(data);
          if (response.success && response.data) {
            tokenManager.setTokens(
              response.data.access_token,
              response.data.refresh_token
            );
            set({
              isAuthenticated: true,
              tenantId: response.data.tenant_id,
              userEmail: data.email,
              isLoading: false,
            });
            return true;
          } else {
            set({
              error: response.error?.message || '登录失败',
              isLoading: false,
            });
            return false;
          }
        } catch (error: unknown) {
          // Handle axios error with response data
          let message = '登录失败，请稍后重试';
          if (error && typeof error === 'object' && 'response' in error) {
            const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
            message = axiosError.response?.data?.error?.message || message;
          } else if (error instanceof Error) {
            message = error.message;
          }
          set({ error: message, isLoading: false });
          return false;
        }
      },

      register: async (data: RegisterRequest) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.register(data);
          if (response.success && response.data) {
            set({ isLoading: false });
            return {
              success: true,
              apiKey: response.data.api_key,
            };
          } else {
            set({
              error: response.error?.message || '注册失败',
              isLoading: false,
            });
            return { success: false };
          }
        } catch (error: unknown) {
          // Handle axios error with response data
          let message = '注册失败，请稍后重试';
          if (error && typeof error === 'object' && 'response' in error) {
            const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
            message = axiosError.response?.data?.error?.message || message;
          } else if (error instanceof Error) {
            message = error.message;
          }
          set({ error: message, isLoading: false });
          return { success: false };
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try {
          const refreshToken = tokenManager.getRefreshToken();
          if (refreshToken) {
            await authApi.logout(refreshToken);
          }
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          tokenManager.clearTokens();
          set({
            isAuthenticated: false,
            tenant: null,
            tenantId: null,
            userEmail: null,
            isLoading: false,
          });
        }
      },

      checkAuth: () => {
        const token = tokenManager.getAccessToken();
        const isAuth = !!token;
        if (!isAuth && get().isAuthenticated) {
          set({ isAuthenticated: false, tenant: null, tenantId: null, userEmail: null });
        }
        return isAuth;
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        tenantId: state.tenantId,
        userEmail: state.userEmail,
      }),
    }
  )
);

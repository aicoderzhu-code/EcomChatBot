import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { adminAuthApi, adminTokenManager } from '@/lib/api/admin';
import { AdminInfo, AdminLoginRequest } from '@/types/admin';

interface AdminState {
  isAuthenticated: boolean;
  isLoading: boolean;
  admin: AdminInfo | null;
  error: string | null;

  login: (data: AdminLoginRequest) => Promise<boolean>;
  logout: () => void;
  checkAdminAuth: () => boolean;
  hasPermission: (permission: string) => boolean;
  clearError: () => void;
}

export const useAdminStore = create<AdminState>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      isLoading: false,
      admin: null,
      error: null,

      login: async (data: AdminLoginRequest) => {
        set({ isLoading: true, error: null });
        try {
          const response = await adminAuthApi.login(data);
          if (response.success && response.data) {
            adminTokenManager.setToken(response.data.access_token);
            set({
              isAuthenticated: true,
              admin: response.data.admin,
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
          let message = '登录失败，请稍后重试';
          if (error && typeof error === 'object' && 'response' in error) {
            const axiosError = error as { response?: { data?: { error?: { message?: string }; detail?: string } } };
            message = axiosError.response?.data?.error?.message ||
                     axiosError.response?.data?.detail ||
                     message;
          } else if (error instanceof Error) {
            message = error.message;
          }
          set({ error: message, isLoading: false });
          return false;
        }
      },

      logout: () => {
        adminTokenManager.clearToken();
        set({
          isAuthenticated: false,
          admin: null,
        });
      },

      checkAdminAuth: () => {
        const token = adminTokenManager.getAccessToken();
        const isAuth = !!token;
        if (!isAuth && get().isAuthenticated) {
          set({ isAuthenticated: false, admin: null });
        }
        return isAuth;
      },

      hasPermission: (permission: string) => {
        const { admin } = get();
        if (!admin) return false;
        // Super admin has all permissions
        if (admin.role === 'super_admin') return true;
        // Check if permission is in the admin's permissions array
        return admin.permissions?.includes(permission) || false;
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'admin-storage',
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        admin: state.admin,
      }),
    }
  )
);

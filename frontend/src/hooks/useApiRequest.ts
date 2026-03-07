'use client';

import { useState, useCallback, useRef } from 'react';
import { message } from 'antd';
import { ApiResponse } from '@/types';

interface UseApiRequestOptions<T> {
  /** 成功时的提示消息 */
  successMessage?: string;
  /** 失败时的提示消息（覆盖服务端消息） */
  errorMessage?: string;
  /** 成功回调 */
  onSuccess?: (data: T) => void;
  /** 失败回调 */
  onError?: (error: { code: string; message: string }) => void;
  /** 是否显示错误 toast（默认 true） */
  showError?: boolean;
  /** 是否显示成功 toast（默认 false） */
  showSuccess?: boolean;
}

interface UseApiRequestReturn<T, A extends unknown[]> {
  data: T | null;
  loading: boolean;
  error: { code: string; message: string } | null;
  execute: (...args: A) => Promise<T | null>;
  reset: () => void;
}

/**
 * 通用 API 请求 Hook — 统一 loading / error / data 状态管理
 *
 * @example
 * const { data, loading, error, execute } = useApiRequest(
 *   (id: string) => fetchUser(id),
 *   { successMessage: '加载成功', showError: true }
 * );
 *
 * // 触发请求
 * await execute('user-123');
 */
export function useApiRequest<T, A extends unknown[] = []>(
  apiFn: (...args: A) => Promise<ApiResponse<T>>,
  options: UseApiRequestOptions<T> = {},
): UseApiRequestReturn<T, A> {
  const {
    successMessage,
    errorMessage,
    onSuccess,
    onError,
    showError = true,
    showSuccess = false,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);

  // 防止组件卸载后 setState
  const mountedRef = useRef(true);

  const execute = useCallback(
    async (...args: A): Promise<T | null> => {
      setLoading(true);
      setError(null);

      try {
        const response = await apiFn(...args);

        if (!mountedRef.current) return null;

        if (response.success && response.data !== null) {
          setData(response.data);
          if (showSuccess && successMessage) {
            message.success(successMessage);
          }
          onSuccess?.(response.data);
          return response.data;
        } else {
          const err = response.error || { code: 'UNKNOWN', message: '请求失败' };
          setError(err);
          if (showError) {
            message.error(errorMessage || err.message);
          }
          onError?.(err);
          return null;
        }
      } catch (e) {
        if (!mountedRef.current) return null;

        const err = {
          code: 'NETWORK_ERROR',
          message: e instanceof Error ? e.message : '网络请求失败，请检查连接',
        };
        setError(err);
        if (showError) {
          message.error(errorMessage || err.message);
        }
        onError?.(err);
        return null;
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiFn],
  );

  const reset = useCallback(() => {
    setData(null);
    setLoading(false);
    setError(null);
  }, []);

  return { data, loading, error, execute, reset };
}

/**
 * 简化版 — 仅管理 mutation 操作（无初始数据）
 *
 * @example
 * const { loading, execute } = useApiMutation(
 *   (id: string) => deleteUser(id),
 *   { successMessage: '删除成功', showError: true, showSuccess: true }
 * );
 */
export function useApiMutation<T, A extends unknown[] = []>(
  apiFn: (...args: A) => Promise<ApiResponse<T>>,
  options: UseApiRequestOptions<T> = {},
): Omit<UseApiRequestReturn<T, A>, 'data' | 'reset'> {
  const { loading, error, execute } = useApiRequest(apiFn, {
    showSuccess: true,
    ...options,
  });
  return { loading, error, execute };
}

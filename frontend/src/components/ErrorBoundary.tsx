'use client';

import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { Button, Result } from 'antd';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** 自定义 fallback UI */
  fallback?: ReactNode;
  /** 错误回调 */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * 全局错误边界组件 — 捕获子组件渲染错误并展示友好界面
 *
 * @example
 * <ErrorBoundary>
 *   <App />
 * </ErrorBoundary>
 *
 * @example
 * <ErrorBoundary fallback={<div>出错了</div>}>
 *   <DangerousComponent />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[ErrorBoundary] 捕获到渲染错误:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div style={{ padding: 48, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
          <Result
            status="error"
            title="页面出现错误"
            subTitle={
              process.env.NODE_ENV === 'development' && this.state.error
                ? this.state.error.message
                : '请尝试刷新页面或联系管理员'
            }
            extra={[
              <Button key="retry" type="primary" onClick={this.handleReset}>
                重试
              </Button>,
              <Button key="reload" onClick={this.handleReload}>
                刷新页面
              </Button>,
            ]}
          />
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

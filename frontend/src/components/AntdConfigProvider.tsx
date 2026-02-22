'use client';

import { ConfigProvider, App } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { ReactNode } from 'react';

const theme = {
  token: {
    colorPrimary: '#2563eb',
    borderRadius: 6,
    colorBgContainer: '#ffffff',
  },
};

interface AntdConfigProviderProps {
  children: ReactNode;
}

export default function AntdConfigProvider({ children }: AntdConfigProviderProps) {
  return (
    <ConfigProvider locale={zhCN} theme={theme}>
      <App>{children}</App>
    </ConfigProvider>
  );
}

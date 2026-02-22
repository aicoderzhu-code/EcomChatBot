'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Form, Input, Button, Card, Typography, Alert, Space } from 'antd';
import { UserOutlined, LockOutlined, SettingOutlined } from '@ant-design/icons';
import { useAdminStore } from '@/store';
import { AdminLoginRequest } from '@/types/admin';

const { Title, Text } = Typography;

export default function AdminLoginPage() {
  const router = useRouter();
  const { login, isLoading, error, clearError, isAuthenticated, checkAdminAuth } = useAdminStore();
  const [form] = Form.useForm();

  useEffect(() => {
    // If already authenticated, redirect to platform
    if (checkAdminAuth() && isAuthenticated) {
      router.push('/platform');
    }
  }, [checkAdminAuth, isAuthenticated, router]);

  const handleSubmit = async (values: AdminLoginRequest) => {
    clearError();
    const success = await login(values);
    if (success) {
      router.push('/platform');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-blue-900">
      <Card className="w-full max-w-md shadow-2xl" bordered={false}>
        <div className="text-center mb-8">
          <Space direction="vertical" size="small">
            <SettingOutlined className="text-5xl text-blue-600" />
            <Title level={2} className="mb-0">
              平台管理后台
            </Title>
            <Text type="secondary">电商智能客服管理系统</Text>
          </Space>
        </div>

        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            closable
            onClose={clearError}
            className="mb-4"
          />
        )}

        <Form
          form={form}
          name="admin_login"
          onFinish={handleSubmit}
          size="large"
          layout="vertical"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input
              prefix={<UserOutlined className="text-gray-400" />}
              placeholder="用户名"
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined className="text-gray-400" />}
              placeholder="密码"
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item className="mb-0">
            <Button
              type="primary"
              htmlType="submit"
              loading={isLoading}
              block
              size="large"
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <div className="mt-6 text-center">
          <Text type="secondary" className="text-xs">
            仅限平台管理员登录
          </Text>
        </div>
      </Card>
    </div>
  );
}

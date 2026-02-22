'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Form, Input, Button, Card, Typography, message, Modal, Alert } from 'antd';
import {
  MailOutlined,
  LockOutlined,
  ShoppingCartOutlined,
  UserOutlined,
  PhoneOutlined,
  BankOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '@/store';

const { Title, Text, Paragraph } = Typography;

interface RegisterFormValues {
  company_name: string;
  contact_name: string;
  contact_email: string;
  contact_phone?: string;
  password: string;
  confirm_password: string;
}

export default function RegisterPage() {
  const router = useRouter();
  const { register, isLoading, error, clearError } = useAuthStore();
  const [form] = Form.useForm();
  const [apiKeyModal, setApiKeyModal] = useState(false);
  const [apiKey, setApiKey] = useState('');

  const onFinish = async (values: RegisterFormValues) => {
    clearError();

    const result = await register({
      company_name: values.company_name,
      contact_name: values.contact_name,
      contact_email: values.contact_email,
      contact_phone: values.contact_phone,
      password: values.password,
    });

    if (result.success && result.apiKey) {
      setApiKey(result.apiKey);
      setApiKeyModal(true);
    } else if (error) {
      message.error(error);
    }
  };

  const handleModalClose = () => {
    setApiKeyModal(false);
    message.success('注册成功，请登录');
    router.push('/login');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 py-12 px-4">
      <Card className="w-full max-w-md shadow-lg">
        <div className="text-center mb-6">
          <ShoppingCartOutlined className="text-5xl text-blue-600 mb-4" />
          <Title level={3} className="mb-1">
            注册新账户
          </Title>
          <Text type="secondary">开始使用智能客服平台</Text>
        </div>

        <Form
          form={form}
          name="register"
          onFinish={onFinish}
          autoComplete="off"
          layout="vertical"
        >
          <Form.Item
            name="company_name"
            label="公司名称"
            rules={[{ required: true, message: '请输入公司名称' }]}
          >
            <Input
              prefix={<BankOutlined className="text-gray-400" />}
              placeholder="请输入公司名称"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="contact_name"
            label="联系人姓名"
            rules={[{ required: true, message: '请输入联系人姓名' }]}
          >
            <Input
              prefix={<UserOutlined className="text-gray-400" />}
              placeholder="请输入联系人姓名"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="contact_email"
            label="联系邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input
              prefix={<MailOutlined className="text-gray-400" />}
              placeholder="请输入联系邮箱"
              size="large"
            />
          </Form.Item>

          <Form.Item name="contact_phone" label="联系电话">
            <Input
              prefix={<PhoneOutlined className="text-gray-400" />}
              placeholder="请输入联系电话（选填）"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码长度至少为8位' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined className="text-gray-400" />}
              placeholder="请输入密码（至少8位）"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="confirm_password"
            label="确认密码"
            dependencies={['password']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined className="text-gray-400" />}
              placeholder="请再次输入密码"
              size="large"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              block
              loading={isLoading}
            >
              注册
            </Button>
          </Form.Item>

          <div className="text-center">
            <Text type="secondary">
              已有账号?{' '}
              <Link href="/login" className="text-blue-600 hover:text-blue-500">
                立即登录
              </Link>
            </Text>
          </div>
        </Form>
      </Card>

      <Modal
        title="注册成功"
        open={apiKeyModal}
        onOk={handleModalClose}
        onCancel={handleModalClose}
        okText="前往登录"
        cancelButtonProps={{ style: { display: 'none' } }}
      >
        <Alert
          message="请妥善保存您的 API Key"
          description="API Key 仅显示一次，请立即复制保存。"
          type="warning"
          showIcon
          className="mb-4"
        />
        <div className="bg-gray-100 p-3 rounded flex items-center justify-between">
          <Paragraph copyable={{ text: apiKey }} className="mb-0 font-mono text-sm break-all">
            {apiKey}
          </Paragraph>
        </div>
      </Modal>
    </div>
  );
}

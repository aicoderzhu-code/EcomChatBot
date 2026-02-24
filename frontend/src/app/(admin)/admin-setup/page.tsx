'use client';

import { useState, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Form, Input, Button, Card, Typography, Steps, Progress, Alert, Space, Result } from 'antd';
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  PhoneOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import { setupApi } from '@/lib/api/admin';
import { InitialAdminCreate } from '@/types/admin';

const { Title, Text, Paragraph } = Typography;

// Password strength calculation
const getPasswordStrength = (password: string): { level: 'weak' | 'medium' | 'strong'; score: number } => {
  if (!password) return { level: 'weak', score: 0 };

  let score = 0;

  // Length scoring
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;

  // Character type scoring
  if (/[a-z]/.test(password)) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score += 1;

  const percent = Math.round((score / 6) * 100);

  if (score <= 2) return { level: 'weak', score: percent };
  if (score <= 4) return { level: 'medium', score: percent };
  return { level: 'strong', score: percent };
};

const strengthColors = {
  weak: '#ff4d4f',
  medium: '#faad14',
  strong: '#52c41a',
};

const strengthLabels = {
  weak: '弱',
  medium: '中',
  strong: '强',
};

export default function AdminSetupPage() {
  const router = useRouter();
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdUsername, setCreatedUsername] = useState<string>('');
  const [password, setPassword] = useState('');

  const passwordStrength = useMemo(() => getPasswordStrength(password), [password]);

  const handleNext = () => {
    setCurrentStep(1);
  };

  const handleSubmit = async (values: InitialAdminCreate) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await setupApi.initialize(values);
      if (response.success && response.data) {
        setCreatedUsername(response.data.username);
        setCurrentStep(2);
      } else {
        setError(response.error?.message || '初始化失败，请稍后重试');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '初始化失败，请稍后重试';
      // Extract error message from axios error response
      if (typeof err === 'object' && err !== null && 'response' in err) {
        const axiosError = err as { response?: { data?: { error?: { message?: string }; detail?: string } } };
        const detail = axiosError.response?.data?.detail || axiosError.response?.data?.error?.message;
        if (detail) {
          setError(detail);
        } else {
          setError(errorMessage);
        }
      } else {
        setError(errorMessage);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoToLogin = useCallback(() => {
    router.push('/admin-login');
  }, [router]);

  // Step 1: Welcome
  const WelcomeStep = (
    <div className="text-center">
      <RocketOutlined className="text-6xl text-blue-500 mb-4" />
      <Title level={2}>欢迎使用电商智能客服平台</Title>
      <Paragraph className="text-gray-500 mb-6">
        系统检测到这是首次部署，需要创建一个超级管理员账户来管理平台。
      </Paragraph>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-left">
        <Title level={5} className="text-blue-700 mb-2">
          <SafetyOutlined className="mr-2" />
          安全提示
        </Title>
        <ul className="text-blue-600 text-sm space-y-1 list-disc list-inside">
          <li>请妥善保管您的管理员账户信息</li>
          <li>密码需包含大小写字母和数字</li>
          <li>首个创建的账户将成为超级管理员</li>
        </ul>
      </div>
      <Button type="primary" size="large" onClick={handleNext}>
        开始设置
      </Button>
    </div>
  );

  // Step 2: Create Account Form
  const CreateAccountStep = (
    <div>
      <div className="text-center mb-6">
        <UserOutlined className="text-4xl text-blue-500 mb-2" />
        <Title level={3}>创建超级管理员</Title>
        <Text type="secondary">请填写管理员账户信息</Text>
      </div>

      {error && (
        <Alert
          message={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
          className="mb-4"
        />
      )}

      <Form
        form={form}
        name="setup_form"
        onFinish={handleSubmit}
        layout="vertical"
        size="large"
      >
        <Form.Item
          name="username"
          label="用户名"
          rules={[
            { required: true, message: '请输入用户名' },
            { min: 3, message: '用户名至少3个字符' },
            { max: 64, message: '用户名最多64个字符' },
            {
              pattern: /^[a-zA-Z][a-zA-Z0-9_]*$/,
              message: '用户名必须以字母开头，只能包含字母、数字和下划线'
            },
          ]}
        >
          <Input
            prefix={<UserOutlined className="text-gray-400" />}
            placeholder="输入管理员用户名"
            autoComplete="username"
          />
        </Form.Item>

        <Form.Item
          name="email"
          label="邮箱"
          rules={[
            { required: true, message: '请输入邮箱' },
            { type: 'email', message: '请输入有效的邮箱地址' },
          ]}
        >
          <Input
            prefix={<MailOutlined className="text-gray-400" />}
            placeholder="输入管理员邮箱"
            autoComplete="email"
          />
        </Form.Item>

        <Form.Item
          name="phone"
          label="手机号（选填）"
          rules={[
            { max: 20, message: '手机号最多20个字符' },
          ]}
        >
          <Input
            prefix={<PhoneOutlined className="text-gray-400" />}
            placeholder="输入手机号"
            autoComplete="tel"
          />
        </Form.Item>

        <Form.Item
          name="password"
          label="密码"
          rules={[
            { required: true, message: '请输入密码' },
            { min: 8, message: '密码至少8个字符' },
            { max: 64, message: '密码最多64个字符' },
            {
              validator: (_, value) => {
                if (!value) return Promise.resolve();
                if (!/[a-z]/.test(value)) {
                  return Promise.reject(new Error('密码必须包含小写字母'));
                }
                if (!/[A-Z]/.test(value)) {
                  return Promise.reject(new Error('密码必须包含大写字母'));
                }
                if (!/\d/.test(value)) {
                  return Promise.reject(new Error('密码必须包含数字'));
                }
                return Promise.resolve();
              },
            },
          ]}
        >
          <Input.Password
            prefix={<LockOutlined className="text-gray-400" />}
            placeholder="设置密码（至少8位，包含大小写字母和数字）"
            autoComplete="new-password"
            onChange={(e) => setPassword(e.target.value)}
          />
        </Form.Item>

        {password && (
          <div className="mb-4">
            <div className="flex items-center justify-between mb-1">
              <Text type="secondary" className="text-sm">密码强度</Text>
              <Text style={{ color: strengthColors[passwordStrength.level] }} className="text-sm font-medium">
                {strengthLabels[passwordStrength.level]}
              </Text>
            </div>
            <Progress
              percent={passwordStrength.score}
              showInfo={false}
              strokeColor={strengthColors[passwordStrength.level]}
              size="small"
            />
          </div>
        )}

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
            placeholder="再次输入密码"
            autoComplete="new-password"
          />
        </Form.Item>

        <Form.Item className="mb-0">
          <Space className="w-full justify-between">
            <Button onClick={() => setCurrentStep(0)}>
              上一步
            </Button>
            <Button type="primary" htmlType="submit" loading={isLoading}>
              创建管理员
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </div>
  );

  // Step 3: Complete
  const CompleteStep = (
    <Result
      icon={<CheckCircleOutlined className="text-green-500" />}
      status="success"
      title="系统初始化完成！"
      subTitle={
        <div>
          <Paragraph>
            超级管理员账户 <Text strong>{createdUsername}</Text> 已创建成功
          </Paragraph>
          <Paragraph type="secondary">
            您现在可以使用此账户登录管理后台
          </Paragraph>
        </div>
      }
      extra={
        <Button type="primary" size="large" onClick={handleGoToLogin}>
          前往登录
        </Button>
      }
    />
  );

  const steps = [
    { title: '欢迎', icon: <RocketOutlined /> },
    { title: '创建账户', icon: <UserOutlined /> },
    { title: '完成', icon: <CheckCircleOutlined /> },
  ];

  const stepContents = [WelcomeStep, CreateAccountStep, CompleteStep];

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-blue-900 p-4">
      <Card className="w-full max-w-lg shadow-2xl" bordered={false}>
        <Steps
          current={currentStep}
          items={steps}
          className="mb-8"
          size="small"
        />
        {stepContents[currentStep]}
      </Card>
    </div>
  );
}

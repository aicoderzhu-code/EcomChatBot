'use client';

import { useState, useEffect } from 'react';
import { Row, Col, Card, Typography, message, Alert, Form, Input, Button, Slider, Spin, Tag } from 'antd';
import { SettingsMenu, ModelConfigForm, SubscriptionPanel } from '@/components/settings';
import { CopyOutlined, LinkOutlined, DisconnectOutlined } from '@ant-design/icons';
import { useAuthStore } from '@/store';
import { platformApi, PlatformConfig } from '@/lib/api/platform';

const { Title, Text } = Typography;

export default function SettingsPage() {
  const [selectedMenu, setSelectedMenu] = useState('model');
  const { tenantId } = useAuthStore();
  const [pddConfig, setPddConfig] = useState<PlatformConfig | null>(null);
  const [pddLoading, setPddLoading] = useState(false);
  const [pddForm] = Form.useForm();

  useEffect(() => {
    if (selectedMenu === 'platform') {
      setPddLoading(true);
      platformApi.getConfigs().then((res) => {
        if (res.success && res.data) {
          const cfg = res.data.find((c) => c.platform_type === 'pinduoduo') ?? null;
          setPddConfig(cfg);
          if (cfg) {
            pddForm.setFieldsValue({
              app_key: cfg.app_key,
              auto_reply_threshold: Math.round(cfg.auto_reply_threshold * 100),
              human_takeover_message: cfg.human_takeover_message ?? '',
            });
          }
        }
      }).finally(() => setPddLoading(false));
    }
  }, [selectedMenu]);

  const renderContent = () => {
    switch (selectedMenu) {
      case 'model':
        return <ModelConfigForm />;
      case 'api':
        return (
          <Card>
            <Title level={5} className="mb-4">API 密钥管理</Title>
            <Alert
              message="API 密钥用于外部系统接入"
              description="您可以使用此 API 密钥将智能客服集成到您的应用中。请妥善保管，不要泄露给他人。"
              type="info"
              showIcon
              className="mb-6"
            />
            <div className="bg-gray-100 p-4 rounded-lg">
              <Text type="secondary" className="block mb-2">租户 ID:</Text>
              <div className="flex items-center gap-2 mb-4">
                <Input
                  value={tenantId || ''}
                  readOnly
                  style={{ flex: 1, fontFamily: 'monospace' }}
                />
                <Button
                  icon={<CopyOutlined />}
                  onClick={() => {
                    if (tenantId) {
                      navigator.clipboard.writeText(tenantId);
                      message.success('已复制到剪贴板');
                    }
                  }}
                >
                  复制
                </Button>
              </div>
              <Text type="secondary" className="block mb-2">API Key (使用JWT Token认证):</Text>
              <div className="flex items-center gap-2">
                <Input.Password
                  value="请使用登录后获取的 access_token"
                  readOnly
                  style={{ flex: 1, fontFamily: 'monospace' }}
                />
              </div>
            </div>
            <Alert
              message="认证方式"
              description="API 请求需要在 Header 中添加 Authorization: Bearer {access_token}"
              type="info"
              showIcon
              className="mt-4"
            />
          </Card>
        );
      case 'tenant':
        return (
          <Card>
            <Title level={5} className="mb-4">租户信息</Title>
            <Form layout="vertical">
              <Form.Item label="租户 ID">
                <Input value={tenantId || ''} disabled />
              </Form.Item>
              <Form.Item label="当前套餐">
                <Input value="专业版" disabled />
              </Form.Item>
              <Alert
                message="如需修改租户信息，请联系管理员"
                type="info"
                showIcon
              />
            </Form>
          </Card>
        );
      case 'notification':
        return (
          <Card>
            <Title level={5} className="mb-4">通知设置</Title>
            <Alert
              message="通知功能即将上线"
              description="我们正在开发通知功能，包括邮件通知、短信通知和 Webhook 回调等。敬请期待！"
              type="info"
              showIcon
            />
          </Card>
        );
      case 'subscription':
        return <SubscriptionPanel />;
      case 'platform':
        return (
          <>
            <Title level={5} className="mb-4">平台对接 - 拼多多</Title>
            <Spin spinning={pddLoading}>
              <div className="mb-4 flex items-center gap-2">
                <span>连接状态：</span>
                {pddConfig?.is_active
                  ? <Tag color="success">已连接 · {pddConfig.shop_name || pddConfig.shop_id}</Tag>
                  : <Tag color="default">未连接</Tag>}
              </div>
              <Form form={pddForm} layout="vertical" onFinish={async (values) => {
                try {
                  const res = await platformApi.upsertConfig('pinduoduo', {
                    app_key: values.app_key,
                    app_secret: values.app_secret,
                    auto_reply_threshold: values.auto_reply_threshold / 100,
                    human_takeover_message: values.human_takeover_message || null,
                  });
                  if (res.success) {
                    setPddConfig(res.data);
                    message.success('配置已保存');
                  }
                } catch {
                  message.error('保存失败');
                }
              }}>
                <Form.Item label="App Key" name="app_key" rules={[{ required: true }]}>
                  <Input placeholder="拼多多开放平台 App Key" />
                </Form.Item>
                <Form.Item label="App Secret" name="app_secret" rules={[{ required: true }]}>
                  <Input.Password placeholder="拼多多开放平台 App Secret" />
                </Form.Item>
                <Form.Item label="自动回复置信度阈值" name="auto_reply_threshold" initialValue={70}>
                  <Slider min={0} max={100} marks={{ 0: '0%', 50: '50%', 70: '70%', 100: '100%' }} />
                </Form.Item>
                <Form.Item label="转人工提示语" name="human_takeover_message">
                  <Input.TextArea placeholder="例如：您好，正在为您转接人工客服，请稍候..." rows={2} />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" className="mr-2">保存配置</Button>
                  {pddConfig && !pddConfig.is_active && (
                    <Button
                      icon={<LinkOutlined />}
                      onClick={() => {
                        const redirectUri = `${window.location.origin}/api/v1/platform/pinduoduo/callback`;
                        window.location.href = platformApi.getAuthUrl(pddConfig.app_key, redirectUri);
                      }}
                    >
                      连接拼多多
                    </Button>
                  )}
                  {pddConfig?.is_active && (
                    <Button
                      danger
                      icon={<DisconnectOutlined />}
                      onClick={async () => {
                        await platformApi.disconnect('pinduoduo');
                        setPddConfig((prev) => prev ? { ...prev, is_active: false } : null);
                        message.success('已断开连接');
                      }}
                    >
                      断开连接
                    </Button>
                  )}
                </Form.Item>
              </Form>
            </Spin>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <div>
      <Title level={4} className="mb-6">系统设置</Title>
      <Row gutter={24}>
        <Col xs={24} md={6}>
          <SettingsMenu selectedKey={selectedMenu} onSelect={setSelectedMenu} />
        </Col>
        <Col xs={24} md={18}>
          {renderContent()}
        </Col>
      </Row>
    </div>
  );
}

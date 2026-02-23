'use client';

import { useState } from 'react';
import { Row, Col, Card, Typography, message, Alert, Form, Input, Button } from 'antd';
import { SettingsMenu, ModelConfigForm } from '@/components/settings';
import { CopyOutlined } from '@ant-design/icons';
import { useAuthStore } from '@/store';

const { Title, Text } = Typography;

export default function SettingsPage() {
  const [selectedMenu, setSelectedMenu] = useState('model');
  const { tenantId } = useAuthStore();

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

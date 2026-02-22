'use client';

import { useState } from 'react';
import { Modal, Form, Input, Select, message } from 'antd';
import { adminTenantsApi } from '@/lib/api/admin';
import { TenantCreateRequest, TenantWithAPIKey } from '@/types/admin';

interface TenantCreateModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (tenant: TenantWithAPIKey) => void;
}

const planOptions = [
  { value: 'free', label: '免费版' },
  { value: 'basic', label: '基础版' },
  { value: 'professional', label: '专业版' },
  { value: 'enterprise', label: '企业版' },
];

export default function TenantCreateModal({ open, onClose, onSuccess }: TenantCreateModalProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const response = await adminTenantsApi.create(values as TenantCreateRequest);
      if (response.success && response.data) {
        message.success('租户创建成功');
        // Show API key in a modal
        Modal.success({
          title: '租户创建成功',
          content: (
            <div>
              <p>请妥善保管以下 API Key，此信息仅显示一次：</p>
              <code className="block bg-gray-100 p-2 mt-2 break-all">
                {response.data.api_key}
              </code>
            </div>
          ),
          width: 500,
        });
        form.resetFields();
        onSuccess(response.data);
        onClose();
      } else {
        message.error(response.error?.message || '创建失败');
      }
    } catch (error) {
      console.error('Create tenant failed:', error);
      message.error('创建失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="创建租户"
      open={open}
      onOk={handleSubmit}
      onCancel={onClose}
      confirmLoading={loading}
      okText="创建"
      cancelText="取消"
      width={520}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{ initial_plan: 'free' }}
      >
        <Form.Item
          name="company_name"
          label="公司名称"
          rules={[{ required: true, message: '请输入公司名称' }]}
        >
          <Input placeholder="请输入公司名称" />
        </Form.Item>

        <Form.Item
          name="contact_name"
          label="联系人"
          rules={[{ required: true, message: '请输入联系人姓名' }]}
        >
          <Input placeholder="请输入联系人姓名" />
        </Form.Item>

        <Form.Item
          name="contact_email"
          label="联系邮箱"
          rules={[
            { required: true, message: '请输入联系邮箱' },
            { type: 'email', message: '请输入有效的邮箱地址' },
          ]}
        >
          <Input placeholder="请输入联系邮箱" />
        </Form.Item>

        <Form.Item
          name="contact_phone"
          label="联系电话"
        >
          <Input placeholder="请输入联系电话（选填）" />
        </Form.Item>

        <Form.Item
          name="password"
          label="初始密码"
          rules={[
            { required: true, message: '请输入初始密码' },
            { min: 8, message: '密码长度不能少于8位' },
          ]}
        >
          <Input.Password placeholder="请输入初始密码" />
        </Form.Item>

        <Form.Item
          name="initial_plan"
          label="初始套餐"
        >
          <Select options={planOptions} placeholder="请选择套餐" />
        </Form.Item>
      </Form>
    </Modal>
  );
}

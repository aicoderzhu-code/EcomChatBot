'use client';

import { useState } from 'react';
import { Modal, Form, Select, InputNumber, Input, message } from 'antd';
import { adminTenantsApi } from '@/lib/api/admin';

interface TenantQuotaFormProps {
  tenantId: string;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const quotaTypes = [
  { value: 'conversation', label: '对话配额' },
  { value: 'storage', label: '存储配额 (MB)' },
  { value: 'api_calls', label: 'API 调用配额' },
];

export default function TenantQuotaForm({ tenantId, open, onClose, onSuccess }: TenantQuotaFormProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const response = await adminTenantsApi.adjustQuota(
        tenantId,
        values.quota_type,
        values.amount,
        values.reason
      );

      if (response.success) {
        message.success('配额调整成功');
        form.resetFields();
        onSuccess();
        onClose();
      } else {
        message.error(response.error?.message || '调整失败');
      }
    } catch (error) {
      console.error('Adjust quota failed:', error);
      message.error('调整失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="调整配额"
      open={open}
      onOk={handleSubmit}
      onCancel={onClose}
      confirmLoading={loading}
      okText="确认调整"
      cancelText="取消"
    >
      <Form
        form={form}
        layout="vertical"
      >
        <Form.Item
          name="quota_type"
          label="配额类型"
          rules={[{ required: true, message: '请选择配额类型' }]}
        >
          <Select options={quotaTypes} placeholder="请选择配额类型" />
        </Form.Item>

        <Form.Item
          name="amount"
          label="调整数量"
          rules={[{ required: true, message: '请输入调整数量' }]}
          extra="正数为增加，负数为减少"
        >
          <InputNumber
            className="w-full"
            placeholder="请输入调整数量"
          />
        </Form.Item>

        <Form.Item
          name="reason"
          label="调整原因"
        >
          <Input.TextArea
            rows={3}
            placeholder="请输入调整原因（选填）"
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}

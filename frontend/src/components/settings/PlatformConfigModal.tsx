'use client';

import { Modal, Form, Input, InputNumber, message } from 'antd';
import { useEffect } from 'react';
import { PlatformConfig, PlatformConfigUpdate, platformApi } from '@/lib/api/platform';

interface PlatformConfigModalProps {
  visible: boolean;
  config: PlatformConfig | null;
  platform?: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function PlatformConfigModal({
  visible,
  config,
  platform = 'pinduoduo',
  onClose,
  onSuccess,
}: PlatformConfigModalProps) {
  const [form] = Form.useForm();

  useEffect(() => {
    if (visible && config) {
      form.setFieldsValue({
        app_key: config.app_key,
        auto_reply_threshold: config.auto_reply_threshold,
        human_takeover_message: config.human_takeover_message,
      });
    } else if (visible && !config) {
      form.resetFields();
    }
  }, [visible, config, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const data: PlatformConfigUpdate = {
        app_key: values.app_key,
        app_secret: values.app_secret,
        auto_reply_threshold: values.auto_reply_threshold,
        human_takeover_message: values.human_takeover_message,
      };

      await platformApi.upsertConfig(platform, data, config?.id);
      message.success(config ? '更新成功' : '创建成功');
      onSuccess();
    } catch (error) {
      console.error('保存配置失败:', error);
      message.error('保存失败');
    }
  };

  return (
    <Modal
      title={config ? '编辑平台配置' : '添加平台配置'}
      open={visible}
      onOk={handleSubmit}
      onCancel={onClose}
      okText="保存"
      cancelText="取消"
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          auto_reply_threshold: 0.7,
        }}
      >
        <Form.Item
          label="App Key"
          name="app_key"
          rules={[{ required: true, message: '请输入 App Key' }]}
        >
          <Input placeholder="请输入 App Key" />
        </Form.Item>

        <Form.Item
          label="App Secret"
          name="app_secret"
          rules={[{ required: !config, message: '请输入 App Secret' }]}
        >
          <Input.Password placeholder={config ? '留空则不修改' : '请输入 App Secret'} />
        </Form.Item>

        <Form.Item
          label="自动回复阈值"
          name="auto_reply_threshold"
          rules={[{ required: true, message: '请输入自动回复阈值' }]}
        >
          <InputNumber
            min={0}
            max={1}
            step={0.1}
            style={{ width: '100%' }}
            placeholder="0.7"
          />
        </Form.Item>

        <Form.Item
          label="人工接管提示语"
          name="human_takeover_message"
        >
          <Input.TextArea
            rows={3}
            placeholder="当置信度低于阈值时发送给用户的提示语"
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}

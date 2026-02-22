'use client';

import { useState } from 'react';
import { Modal, Upload, message, Typography, Alert } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';

const { Dragger } = Upload;
const { Text } = Typography;

interface UploadModalProps {
  open: boolean;
  onClose: () => void;
  onUpload: (files: File[]) => Promise<void>;
  uploading?: boolean;
}

const acceptedTypes = [
  '.pdf',
  '.docx',
  '.doc',
  '.md',
  '.txt',
];

export default function UploadModal({
  open,
  onClose,
  onUpload,
  uploading = false,
}: UploadModalProps) {
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请选择要上传的文件');
      return;
    }

    const files = fileList
      .filter((f) => f.originFileObj)
      .map((f) => f.originFileObj as File);

    await onUpload(files);
    setFileList([]);
  };

  const handleClose = () => {
    setFileList([]);
    onClose();
  };

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: true,
    accept: acceptedTypes.join(','),
    fileList,
    beforeUpload: (file) => {
      const isValidType = acceptedTypes.some((type) =>
        file.name.toLowerCase().endsWith(type)
      );
      if (!isValidType) {
        message.error(`不支持的文件类型: ${file.name}`);
        return Upload.LIST_IGNORE;
      }
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        message.error('文件大小不能超过 10MB');
        return Upload.LIST_IGNORE;
      }
      return false; // Prevent auto upload
    },
    onChange: ({ fileList: newFileList }) => {
      setFileList(newFileList);
    },
    onRemove: (file) => {
      setFileList((prev) => prev.filter((f) => f.uid !== file.uid));
    },
  };

  return (
    <Modal
      title="上传新文档"
      open={open}
      onOk={handleUpload}
      onCancel={handleClose}
      okText="开始上传"
      cancelText="取消"
      confirmLoading={uploading}
      width={600}
    >
      <Alert
        message="支持的文件格式"
        description="PDF、Word（.docx/.doc）、Markdown（.md）、纯文本（.txt）"
        type="info"
        showIcon
        className="mb-4"
      />

      <Dragger {...uploadProps} className="mb-4">
        <p className="ant-upload-drag-icon">
          <InboxOutlined className="text-4xl text-blue-500" />
        </p>
        <p className="ant-upload-text">
          点击或拖拽文件到此区域上传
        </p>
        <p className="ant-upload-hint">
          支持单个或批量上传，单个文件不超过 10MB
        </p>
      </Dragger>

      {fileList.length > 0 && (
        <div>
          <Text type="secondary">
            已选择 {fileList.length} 个文件
          </Text>
        </div>
      )}
    </Modal>
  );
}

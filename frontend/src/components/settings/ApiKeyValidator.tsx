'use client';

import { memo } from 'react';
import { Input, Button, Alert, Space } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  SearchOutlined,
} from '@ant-design/icons';

export type ValidationStatus = 'idle' | 'validating' | 'valid' | 'invalid';

interface ApiKeyValidatorProps {
  apiKey: string;
  onApiKeyChange: (value: string) => void;
  validationStatus: ValidationStatus;
  validationMsg: string;
  onValidate: () => void;
  /** 是否支持模型发现 */
  canDiscover?: boolean;
  discovering?: boolean;
  onDiscover?: () => void;
  /** API Key 是否可选（私有部署） */
  optional?: boolean;
}

function ApiKeyValidator({
  apiKey,
  onApiKeyChange,
  validationStatus,
  validationMsg,
  onValidate,
  canDiscover = false,
  discovering = false,
  onDiscover,
  optional = false,
}: ApiKeyValidatorProps) {
  return (
    <div className="mb-4">
      <span className="font-semibold block mb-1">
        API Key{' '}
        {optional
          ? <span className="text-neutral-400 font-normal">（可选）</span>
          : <span className="text-red-500">*</span>
        }
      </span>
      <Space.Compact style={{ width: '100%' }}>
        <Input.Password
          value={apiKey}
          onChange={e => onApiKeyChange(e.target.value)}
          placeholder="输入 API Key..."
          style={{ flex: 1 }}
        />
        <Button
          onClick={onValidate}
          loading={validationStatus === 'validating'}
          icon={
            validationStatus === 'valid' ? (
              <CheckCircleOutlined className="text-success-500" />
            ) : validationStatus === 'invalid' ? (
              <CloseCircleOutlined className="text-error-500" />
            ) : validationStatus === 'validating' ? (
              <LoadingOutlined />
            ) : undefined
          }
        >
          {validationStatus === 'validating' ? '验证中' : '验证'}
        </Button>
      </Space.Compact>

      {validationStatus === 'valid' && (
        <Alert className="mt-2" type="success" message={validationMsg} showIcon banner />
      )}
      {validationStatus === 'invalid' && (
        <Alert className="mt-2" type="error" message={validationMsg} showIcon banner />
      )}

      {validationStatus === 'valid' && canDiscover && onDiscover && (
        <div className="mt-3">
          <Button icon={<SearchOutlined />} loading={discovering} onClick={onDiscover}>
            {discovering ? '检测中...' : '检测可用模型'}
          </Button>
        </div>
      )}
    </div>
  );
}

export default memo(ApiKeyValidator);

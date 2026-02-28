'use client';

import { useState, useCallback } from 'react';
import { Modal, message } from 'antd';
import { platformApi, type PlatformConfig } from '@/lib/api/platform';
import { contentApi } from '@/lib/api/content';

export function usePlatformUpload(onSuccess?: () => void) {
  const [uploading, setUploading] = useState(false);

  const uploadAsset = useCallback(async (assetId: number) => {
    setUploading(true);
    try {
      const resp = await platformApi.getConfigs();
      const configs = resp.success ? (resp.data || []) : [];
      const activeConfigs = configs.filter((c: PlatformConfig) => c.is_active);

      if (activeConfigs.length === 0) {
        message.warning('暂无可用的平台配置，请先在设置中配置平台');
        setUploading(false);
        return;
      }

      const doUpload = async (configId: number) => {
        try {
          const uploadResp = await contentApi.uploadAssetToPlatform({
            asset_id: assetId,
            platform_config_id: configId,
          });
          if (uploadResp.success) {
            message.success('已上传到平台');
            onSuccess?.();
          } else {
            message.error(uploadResp.error?.message || '上传失败');
          }
        } catch {
          message.error('上传失败');
        }
      };

      if (activeConfigs.length === 1) {
        await doUpload(activeConfigs[0].id);
      } else {
        // 多个平台时弹窗选择
        Modal.confirm({
          title: '选择上传平台',
          content: (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
              {activeConfigs.map((c: PlatformConfig) => (
                <a
                  key={c.id}
                  onClick={() => {
                    Modal.destroyAll();
                    doUpload(c.id);
                  }}
                  style={{ cursor: 'pointer', padding: '8px 12px', border: '1px solid #d9d9d9', borderRadius: 6 }}
                >
                  {c.platform_type}{c.shop_name ? ` - ${c.shop_name}` : ''}
                </a>
              ))}
            </div>
          ),
          footer: null,
          closable: true,
          maskClosable: true,
        });
      }
    } catch {
      message.error('获取平台配置失败');
    } finally {
      setUploading(false);
    }
  }, [onSuccess]);

  return { uploadAsset, uploading };
}

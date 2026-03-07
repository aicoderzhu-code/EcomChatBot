'use client';

import { useState } from 'react';
import { Card, Segmented, Typography } from 'antd';
import { VideoCameraOutlined, ThunderboltOutlined, SettingOutlined } from '@ant-design/icons';
import SimpleMode from '@/components/content/SimpleMode';
import AdvancedModeVideo from '@/components/content/AdvancedModeVideo';

const { Title } = Typography;

type Mode = 'simple' | 'advanced';

export default function VideoPage() {
  const [mode, setMode] = useState<Mode>('simple');

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>
          <VideoCameraOutlined style={{ marginRight: 8 }} />
          视频生成工作台
        </Title>

        <Segmented
          value={mode}
          onChange={(value) => setMode(value as Mode)}
          options={[
            {
              label: (
                <div style={{ display: 'flex', alignItems: 'center', padding: '0 8px' }}>
                  <ThunderboltOutlined style={{ marginRight: 4 }} />
                  <span>简易模式</span>
                </div>
              ),
              value: 'simple',
            },
            {
              label: (
                <div style={{ display: 'flex', alignItems: 'center', padding: '0 8px' }}>
                  <SettingOutlined style={{ marginRight: 4 }} />
                  <span>专业模式</span>
                </div>
              ),
              value: 'advanced',
            },
          ]}
        />
      </div>

      {mode === 'simple' ? (
        <Card>
          <SimpleMode category="video" />
        </Card>
      ) : (
        <AdvancedModeVideo />
      )}
    </div>
  );
}

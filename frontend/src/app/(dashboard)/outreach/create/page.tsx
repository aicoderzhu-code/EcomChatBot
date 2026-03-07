'use client';

import { useState, useEffect } from 'react';
import {
  Card, Steps, Button, Space, message, Form, Input, Select,
  DatePicker, InputNumber, Radio, List, Tag,
} from 'antd';
import { useRouter } from 'next/navigation';
import { campaignApi, segmentApi } from '@/lib/api/outreach';
import { platformApi, type PlatformConfig } from '@/lib/api/platform';
import type { CustomerSegment, ContentStrategy } from '@/types';

const { TextArea } = Input;

export default function CreateCampaignPage() {
  const router = useRouter();
  const [current, setCurrent] = useState(0);
  const [loading, setLoading] = useState(false);

  // Step 1: 选择分群
  const [segments, setSegments] = useState<CustomerSegment[]>([]);
  const [selectedSegmentId, setSelectedSegmentId] = useState<number | null>(null);
  const [segmentsLoading, setSegmentsLoading] = useState(false);

  // Step 2: 内容策略
  const [contentStrategy, setContentStrategy] = useState<ContentStrategy>('template');
  const [contentTemplate, setContentTemplate] = useState('');
  const [aiPrompt, setAiPrompt] = useState('');

  // Step 3: 调度设置
  const [scheduledAt, setScheduledAt] = useState<string | null>(null);
  const [maxPerUserPerDay, setMaxPerUserPerDay] = useState(1);
  const [cooldownHours, setCooldownHours] = useState(24);
  const [platformConfigId, setPlatformConfigId] = useState<number | null>(null);
  const [platformConfigs, setPlatformConfigs] = useState<PlatformConfig[]>([]);

  // Campaign name
  const [campaignName, setCampaignName] = useState('');

  useEffect(() => {
    loadSegments();
    loadPlatformConfigs();
  }, []);

  const loadSegments = async () => {
    setSegmentsLoading(true);
    try {
      const resp = await segmentApi.list({ page: 1, size: 100 });
      if (resp.success && resp.data) {
        setSegments(resp.data.items);
      }
    } catch {
      message.error('加载分群列表失败');
    } finally {
      setSegmentsLoading(false);
    }
  };

  const loadPlatformConfigs = async () => {
    try {
      const resp = await platformApi.getConfigs();
      if (resp.success && resp.data) {
        const activeConfigs = resp.data.filter(c => c.is_active);
        setPlatformConfigs(activeConfigs);
        if (activeConfigs.length > 0) {
          setPlatformConfigId(activeConfigs[0].id);
        }
      }
    } catch {
      message.error('加载平台配置失败');
    }
  };

  const handleNext = () => {
    if (current === 0 && !selectedSegmentId) {
      message.warning('请选择目标分群');
      return;
    }
    if (current === 1) {
      if (contentStrategy === 'template' && !contentTemplate.trim()) {
        message.warning('请填写内容模板');
        return;
      }
      if (contentStrategy === 'ai_generated' && !aiPrompt.trim()) {
        message.warning('请填写AI生成提示词');
        return;
      }
    }
    if (current === 2 && !platformConfigId) {
      message.warning('请选择平台配置');
      return;
    }
    setCurrent(current + 1);
  };

  const handlePrev = () => {
    setCurrent(current - 1);
  };

  const handleSubmit = async () => {
    if (!campaignName.trim()) {
      message.warning('请填写活动名称');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        name: campaignName.trim(),
        campaign_type: 'manual',
        segment_id: selectedSegmentId,
        content_strategy: contentStrategy,
        content_template: contentStrategy === 'template' ? contentTemplate : null,
        ai_prompt: contentStrategy === 'ai_generated' ? aiPrompt : null,
        scheduled_at: scheduledAt,
        max_per_user_per_day: maxPerUserPerDay,
        cooldown_hours: cooldownHours,
        platform_config_id: platformConfigId,
      };

      const resp = await campaignApi.create(payload);
      if (resp.success) {
        message.success('活动创建成功');
        router.push('/outreach');
      } else {
        message.error(resp.error?.message || '创建失败');
      }
    } catch {
      message.error('创建失败');
    } finally {
      setLoading(false);
    }
  };

  const steps = [
    { title: '选择分群' },
    { title: '内容策略' },
    { title: '调度设置' },
    { title: '确认' },
  ];

  const selectedSegment = segments.find(s => s.id === selectedSegmentId);

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24 }}>创建外呼活动</h2>

      <Card>
        <Steps current={current} items={steps} style={{ marginBottom: 32 }} />

        {current === 0 && (
          <div>
            <h3>选择目标分群</h3>
            <List
              loading={segmentsLoading}
              dataSource={segments}
              renderItem={(segment) => (
                <List.Item
                  onClick={() => setSelectedSegmentId(segment.id)}
                  style={{
                    cursor: 'pointer',
                    background: selectedSegmentId === segment.id ? '#e6f7ff' : 'transparent',
                    padding: 16,
                    borderRadius: 4,
                  }}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        {segment.name}
                        <Tag color={segment.segment_type === 'dynamic' ? 'blue' : 'default'}>
                          {segment.segment_type === 'dynamic' ? '动态' : '手动'}
                        </Tag>
                      </Space>
                    }
                    description={
                      <Space>
                        <span>{segment.description || '无描述'}</span>
                        <span>成员数: {segment.member_count}</span>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </div>
        )}

        {current === 1 && (
          <div>
            <h3>内容策略</h3>
            <Form layout="vertical">
              <Form.Item label="策略类型">
                <Radio.Group
                  value={contentStrategy}
                  onChange={(e) => setContentStrategy(e.target.value)}
                >
                  <Radio value="template">使用模板</Radio>
                  <Radio value="ai_generated">AI生成</Radio>
                </Radio.Group>
              </Form.Item>

              {contentStrategy === 'template' && (
                <Form.Item label="内容模板">
                  <TextArea
                    rows={6}
                    placeholder="输入消息模板，支持变量如 {name}, {product_name} 等"
                    value={contentTemplate}
                    onChange={(e) => setContentTemplate(e.target.value)}
                  />
                </Form.Item>
              )}

              {contentStrategy === 'ai_generated' && (
                <Form.Item label="AI生成提示词">
                  <TextArea
                    rows={6}
                    placeholder="描述你希望AI生成什么样的内容"
                    value={aiPrompt}
                    onChange={(e) => setAiPrompt(e.target.value)}
                  />
                </Form.Item>
              )}
            </Form>
          </div>
        )}

        {current === 2 && (
          <div>
            <h3>调度设置</h3>
            <Form layout="vertical">
              <Form.Item label="计划发送时间">
                <DatePicker
                  showTime
                  style={{ width: '100%' }}
                  placeholder="选择发送时间（留空立即发送）"
                  onChange={(date) => setScheduledAt(date ? date.toISOString() : null)}
                />
              </Form.Item>

              <Form.Item label="每用户每日最大发送数">
                <InputNumber
                  min={1}
                  max={10}
                  value={maxPerUserPerDay}
                  onChange={(v) => v && setMaxPerUserPerDay(v)}
                  style={{ width: '100%' }}
                />
              </Form.Item>

              <Form.Item label="冷却时间（小时）">
                <InputNumber
                  min={1}
                  max={168}
                  value={cooldownHours}
                  onChange={(v) => v && setCooldownHours(v)}
                  style={{ width: '100%' }}
                />
              </Form.Item>

              <Form.Item label="平台配置">
                <Select
                  value={platformConfigId}
                  onChange={setPlatformConfigId}
                  style={{ width: '100%' }}
                  options={platformConfigs.map(c => ({
                    value: c.id,
                    label: `${c.shop_name || c.shop_id || '未命名'} (${c.platform_type})`,
                  }))}
                />
              </Form.Item>
            </Form>
          </div>
        )}

        {current === 3 && (
          <div>
            <h3>确认信息</h3>
            <Form layout="vertical">
              <Form.Item label="活动名称" required>
                <Input
                  placeholder="输入活动名称"
                  value={campaignName}
                  onChange={(e) => setCampaignName(e.target.value)}
                />
              </Form.Item>
            </Form>

            <Card size="small" title="活动概览" style={{ marginTop: 16 }}>
              <p><strong>目标分群:</strong> {selectedSegment?.name} ({selectedSegment?.member_count} 人)</p>
              <p><strong>内容策略:</strong> {contentStrategy === 'template' ? '使用模板' : 'AI生成'}</p>
              {contentStrategy === 'template' && (
                <p><strong>内容模板:</strong> {contentTemplate}</p>
              )}
              {contentStrategy === 'ai_generated' && (
                <p><strong>AI提示词:</strong> {aiPrompt}</p>
              )}
              <p><strong>发送时间:</strong> {scheduledAt ? new Date(scheduledAt).toLocaleString('zh-CN') : '立即发送'}</p>
              <p><strong>每日限制:</strong> {maxPerUserPerDay} 条/用户</p>
              <p><strong>冷却时间:</strong> {cooldownHours} 小时</p>
            </Card>
          </div>
        )}

        <div style={{ marginTop: 24 }}>
          <Space>
            {current > 0 && (
              <Button onClick={handlePrev}>上一步</Button>
            )}
            {current < steps.length - 1 && (
              <Button type="primary" onClick={handleNext}>下一步</Button>
            )}
            {current === steps.length - 1 && (
              <Button type="primary" loading={loading} onClick={handleSubmit}>
                创建活动
              </Button>
            )}
            <Button onClick={() => router.push('/outreach')}>取消</Button>
          </Space>
        </div>
      </Card>
    </div>
  );
}


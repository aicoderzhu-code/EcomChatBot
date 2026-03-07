'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Space, Tag, message, Tabs, Popconfirm,
} from 'antd';
import {
  PlusOutlined, PlayCircleOutlined, PauseCircleOutlined,
  StopOutlined, EyeOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useRouter } from 'next/navigation';
import { campaignApi } from '@/lib/api/outreach';
import type { OutreachCampaign, CampaignStatus } from '@/types';

export default function OutreachPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<OutreachCampaign[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  const loadCampaigns = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await campaignApi.list({
        status: statusFilter,
        page,
        size,
      });
      if (resp.success && resp.data) {
        setCampaigns(resp.data.items);
        setTotal(resp.data.total);
      }
    } catch {
      message.error('加载活动列表失败');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page, size]);

  useEffect(() => {
    loadCampaigns();
  }, [loadCampaigns]);

  const handleLaunch = async (id: number) => {
    try {
      const resp = await campaignApi.launch(id);
      if (resp.success) {
        message.success('活动已启动');
        loadCampaigns();
      } else {
        message.error(resp.error?.message || '启动失败');
      }
    } catch {
      message.error('启动失败');
    }
  };

  const handlePause = async (id: number) => {
    try {
      const resp = await campaignApi.pause(id);
      if (resp.success) {
        message.success('活动已暂停');
        loadCampaigns();
      } else {
        message.error(resp.error?.message || '暂停失败');
      }
    } catch {
      message.error('暂停失败');
    }
  };

  const handleResume = async (id: number) => {
    try {
      const resp = await campaignApi.resume(id);
      if (resp.success) {
        message.success('活动已恢复');
        loadCampaigns();
      } else {
        message.error(resp.error?.message || '恢复失败');
      }
    } catch {
      message.error('恢复失败');
    }
  };

  const handleCancel = async (id: number) => {
    try {
      const resp = await campaignApi.cancel(id);
      if (resp.success) {
        message.success('活动已取消');
        loadCampaigns();
      } else {
        message.error(resp.error?.message || '取消失败');
      }
    } catch {
      message.error('取消失败');
    }
  };

  const statusTagMap: Record<CampaignStatus, { color: string; text: string }> = {
    draft: { color: 'default', text: '草稿' },
    scheduled: { color: 'blue', text: '已排期' },
    running: { color: 'processing', text: '进行中' },
    completed: { color: 'success', text: '已完成' },
    paused: { color: 'warning', text: '已暂停' },
    failed: { color: 'error', text: '失败' },
  };

  const campaignTypeMap: Record<string, string> = {
    manual: '手动触发',
    auto_rule: '自动规则',
    follow_up: '定时跟进',
    post_purchase: '售后触达',
  };

  const columns: ColumnsType<OutreachCampaign> = [
    {
      title: '名称',
      dataIndex: 'name',
      ellipsis: true,
      width: 200,
    },
    {
      title: '类型',
      dataIndex: 'campaign_type',
      width: 100,
      render: (type: string) => <Tag>{campaignTypeMap[type] || type}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: CampaignStatus) => {
        const tag = statusTagMap[status];
        return <Tag color={tag.color}>{tag.text}</Tag>;
      },
    },
    {
      title: '目标人数',
      dataIndex: 'total_targets',
      width: 100,
      align: 'right' as const,
    },
    {
      title: '已发送',
      dataIndex: 'sent_count',
      width: 100,
      align: 'right' as const,
    },
    {
      title: '送达',
      dataIndex: 'delivered_count',
      width: 100,
      align: 'right' as const,
    },
    {
      title: '转化',
      dataIndex: 'converted_count',
      width: 100,
      align: 'right' as const,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 160,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: OutreachCampaign) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => router.push(`/outreach/${record.id}`)}
          >
            详情
          </Button>
          {record.status === 'draft' && (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleLaunch(record.id)}
            >
              启动
            </Button>
          )}
          {record.status === 'running' && (
            <Button
              type="link"
              size="small"
              icon={<PauseCircleOutlined />}
              onClick={() => handlePause(record.id)}
            >
              暂停
            </Button>
          )}
          {record.status === 'paused' && (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleResume(record.id)}
            >
              恢复
            </Button>
          )}
          {(record.status === 'draft' || record.status === 'scheduled' || record.status === 'paused') && (
            <Popconfirm
              title="确定取消该活动？"
              onConfirm={() => handleCancel(record.id)}
            >
              <Button
                type="link"
                size="small"
                danger
                icon={<StopOutlined />}
              >
                取消
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  const tabItems = [
    { key: 'all', label: '全部' },
    { key: 'draft', label: '草稿' },
    { key: 'scheduled', label: '已排期' },
    { key: 'running', label: '进行中' },
    { key: 'paused', label: '已暂停' },
    { key: 'completed', label: '已完成' },
    { key: 'failed', label: '失败' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>外呼活动</h2>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => router.push('/outreach/create')}
        >
          创建活动
        </Button>
      </div>

      <Card>
        <Tabs
          activeKey={statusFilter || 'all'}
          onChange={(key) => {
            setStatusFilter(key === 'all' ? undefined : key);
            setPage(1);
          }}
          items={tabItems}
          style={{ marginBottom: 16 }}
        />

        <Table
          columns={columns}
          dataSource={campaigns}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: size,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 个活动`,
            onChange: (p, s) => {
              setPage(p);
              setSize(s);
            },
          }}
        />
      </Card>
    </div>
  );
}


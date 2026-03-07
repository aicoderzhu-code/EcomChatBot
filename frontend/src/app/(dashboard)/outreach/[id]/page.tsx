'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Card, Button, Space, Tag, message, Row, Col, Statistic,
  Progress, Table, Descriptions, Popconfirm,
} from 'antd';
import {
  PlayCircleOutlined, PauseCircleOutlined, StopOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useParams, useRouter } from 'next/navigation';
import { campaignApi } from '@/lib/api/outreach';
import type {
  OutreachCampaign, CampaignStats, OutreachTask,
  CampaignStatus, OutreachTaskStatus,
} from '@/types';

export default function CampaignDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [campaign, setCampaign] = useState<OutreachCampaign | null>(null);
  const [stats, setStats] = useState<CampaignStats | null>(null);
  const [tasks, setTasks] = useState<OutreachTask[]>([]);
  const [tasksTotal, setTasksTotal] = useState(0);
  const [tasksPage, setTasksPage] = useState(1);
  const [tasksSize, setTasksSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [tasksLoading, setTasksLoading] = useState(false);

  const loadCampaign = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await campaignApi.get(id);
      if (resp.success && resp.data) {
        setCampaign(resp.data);
      }
    } catch {
      message.error('加载活动详情失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  const loadStats = useCallback(async () => {
    try {
      const resp = await campaignApi.getStats(id);
      if (resp.success && resp.data) {
        setStats(resp.data);
      }
    } catch {
      // ignore
    }
  }, [id]);

  const loadTasks = useCallback(async () => {
    setTasksLoading(true);
    try {
      const resp = await campaignApi.getTasks(id, {
        page: tasksPage,
        size: tasksSize,
      });
      if (resp.success && resp.data) {
        setTasks(resp.data.items);
        setTasksTotal(resp.data.total);
      }
    } catch {
      message.error('加载任务列表失败');
    } finally {
      setTasksLoading(false);
    }
  }, [id, tasksPage, tasksSize]);

  useEffect(() => {
    loadCampaign();
    loadStats();
    loadTasks();
  }, [loadCampaign, loadStats, loadTasks]);

  const handleLaunch = async () => {
    try {
      const resp = await campaignApi.launch(id);
      if (resp.success) {
        message.success('活动已启动');
        loadCampaign();
        loadStats();
      } else {
        message.error(resp.error?.message || '启动失败');
      }
    } catch {
      message.error('启动失败');
    }
  };

  const handlePause = async () => {
    try {
      const resp = await campaignApi.pause(id);
      if (resp.success) {
        message.success('活动已暂停');
        loadCampaign();
      } else {
        message.error(resp.error?.message || '暂停失败');
      }
    } catch {
      message.error('暂停失败');
    }
  };

  const handleResume = async () => {
    try {
      const resp = await campaignApi.resume(id);
      if (resp.success) {
        message.success('活动已恢复');
        loadCampaign();
      } else {
        message.error(resp.error?.message || '恢复失败');
      }
    } catch {
      message.error('恢复失败');
    }
  };

  const handleCancel = async () => {
    try {
      const resp = await campaignApi.cancel(id);
      if (resp.success) {
        message.success('活动已取消');
        loadCampaign();
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

  const taskStatusTagMap: Record<OutreachTaskStatus, { color: string; text: string }> = {
    pending: { color: 'default', text: '待处理' },
    generating: { color: 'processing', text: '生成中' },
    sending: { color: 'processing', text: '发送中' },
    sent: { color: 'blue', text: '已发送' },
    delivered: { color: 'success', text: '已送达' },
    failed: { color: 'error', text: '失败' },
    cancelled: { color: 'default', text: '已取消' },
    converted: { color: 'green', text: '已转化' },
  };

  const campaignTypeMap: Record<string, string> = {
    manual: '手动触发',
    auto_rule: '自动规则',
    follow_up: '定时跟进',
    post_purchase: '售后触达',
  };

  const taskColumns: ColumnsType<OutreachTask> = [
    {
      title: '用户ID',
      dataIndex: 'user_id',
      width: 100,
    },
    {
      title: '内容预览',
      dataIndex: 'content',
      ellipsis: true,
      render: (content: string | null) => content || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: OutreachTaskStatus) => {
        const tag = taskStatusTagMap[status];
        return <Tag color={tag.color}>{tag.text}</Tag>;
      },
    },
    {
      title: '发送时间',
      dataIndex: 'sent_at',
      width: 160,
      render: (time: string | null) =>
        time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      ellipsis: true,
      render: (msg: string | null) => msg || '-',
    },
  ];

  if (loading || !campaign) {
    return <div style={{ padding: 24 }}>加载中...</div>;
  }

  const statusTag = statusTagMap[campaign.status];
  const sendRate = stats ? stats.send_rate : 0;
  const deliveryRate = stats ? stats.delivery_rate : 0;
  const conversionRate = stats ? stats.conversion_rate : 0;

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => router.push('/outreach')}
          style={{ marginBottom: 16 }}
        >
          返回列表
        </Button>

        <Card>
          <Descriptions title="活动信息" column={2}>
            <Descriptions.Item label="活动名称">{campaign.name}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={statusTag.color}>{statusTag.text}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="类型">
              {campaignTypeMap[campaign.campaign_type] || campaign.campaign_type}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {new Date(campaign.created_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
            {campaign.scheduled_at && (
              <Descriptions.Item label="计划时间">
                {new Date(campaign.scheduled_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
            )}
            {campaign.started_at && (
              <Descriptions.Item label="开始时间">
                {new Date(campaign.started_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
            )}
            {campaign.completed_at && (
              <Descriptions.Item label="完成时间">
                {new Date(campaign.completed_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
            )}
          </Descriptions>

          <div style={{ marginTop: 16 }}>
            <Space>
              {campaign.status === 'draft' && (
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={handleLaunch}
                >
                  启动
                </Button>
              )}
              {campaign.status === 'running' && (
                <Button
                  icon={<PauseCircleOutlined />}
                  onClick={handlePause}
                >
                  暂停
                </Button>
              )}
              {campaign.status === 'paused' && (
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={handleResume}
                >
                  恢复
                </Button>
              )}
              {(campaign.status === 'draft' || campaign.status === 'scheduled' || campaign.status === 'paused') && (
                <Popconfirm
                  title="确定取消该活动？"
                  onConfirm={handleCancel}
                >
                  <Button danger icon={<StopOutlined />}>
                    取消
                  </Button>
                </Popconfirm>
              )}
            </Space>
          </div>
        </Card>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={4}>
          <Card>
            <Statistic
              title="目标人数"
              value={campaign.total_targets}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="已发送"
              value={campaign.sent_count}
              suffix={
                <span style={{ fontSize: 14, color: '#999' }}>
                  / {campaign.total_targets}
                </span>
              }
            />
            <Progress
              percent={Math.round(sendRate * 100)}
              size="small"
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="送达"
              value={campaign.delivered_count}
              valueStyle={{ color: '#52c41a' }}
            />
            <Progress
              percent={Math.round(deliveryRate * 100)}
              size="small"
              strokeColor="#52c41a"
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="失败"
              value={campaign.failed_count}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="点击"
              value={campaign.clicked_count}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="转化"
              value={campaign.converted_count}
              valueStyle={{ color: '#1890ff' }}
            />
            <Progress
              percent={Math.round(conversionRate * 100)}
              size="small"
              strokeColor="#1890ff"
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="任务列表">
        <Table
          columns={taskColumns}
          dataSource={tasks}
          rowKey="id"
          loading={tasksLoading}
          pagination={{
            current: tasksPage,
            pageSize: tasksSize,
            total: tasksTotal,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 个任务`,
            onChange: (p, s) => {
              setTasksPage(p);
              setTasksSize(s);
            },
          }}
        />
      </Card>
    </div>
  );
}


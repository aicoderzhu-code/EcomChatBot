'use client';

import { Card, Table, Tag, Typography } from 'antd';
import { useRouter } from 'next/navigation';
import type { ColumnsType } from 'antd/es/table';
import { Conversation } from '@/types';

const { Title, Link: AntLink } = Typography;

interface RecentConversationsProps {
  conversations: Conversation[];
  loading?: boolean;
}

const statusConfig: Record<string, { color: string; text: string }> = {
  active: { color: 'green', text: '进行中' },
  waiting: { color: 'red', text: '待人工' },
  closed: { color: 'default', text: '已结束' },
};

export default function RecentConversations({
  conversations,
  loading = false,
}: RecentConversationsProps) {
  const router = useRouter();

  const columns: ColumnsType<Conversation> = [
    {
      title: '会话ID',
      dataIndex: 'conversation_id',
      key: 'conversation_id',
      render: (id: string) => `#${id.slice(0, 8).toUpperCase()}`,
    },
    {
      title: '用户',
      dataIndex: 'user_external_id',
      key: 'user',
      render: (id: string) => `访客_${id.slice(-4)}`,
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (date: string) => {
        const d = new Date(date);
        return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
      },
    },
    {
      title: '消息数',
      dataIndex: 'message_count',
      key: 'message_count',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config = statusConfig[status] || statusConfig.closed;
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => {
        const isWaiting = record.status === 'waiting';
        return (
          <AntLink
            onClick={() => router.push(`/chat?id=${record.conversation_id}`)}
          >
            {isWaiting ? '接管' : record.status === 'active' ? '查看' : '详情'}
          </AntLink>
        );
      },
    },
  ];

  return (
    <Card>
      <Title level={5} className="mb-4">
        最近活跃会话
      </Title>
      <Table
        columns={columns}
        dataSource={conversations}
        rowKey="conversation_id"
        loading={loading}
        pagination={false}
        size="middle"
      />
    </Card>
  );
}

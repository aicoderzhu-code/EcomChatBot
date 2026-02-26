'use client';

import { memo } from 'react';
import { Input, List, Tag, Typography, Spin, Segmented, Pagination } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { Conversation } from '@/types';

const { Text } = Typography;

type StatusFilter = 'all' | 'active' | 'waiting' | 'closed';

interface ConversationListProps {
  conversations: Conversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading?: boolean;
  searchValue: string;
  onSearchChange: (value: string) => void;
  statusFilter?: StatusFilter;
  onStatusFilterChange?: (status: StatusFilter) => void;
  pagination?: { page: number; total: number; size: number };
  onPageChange?: (page: number) => void;
}

const statusConfig: Record<string, { color: string; text: string }> = {
  active: { color: 'green', text: 'AI 处理中' },
  waiting: { color: 'red', text: '待人工接入' },
  closed: { color: 'default', text: '已结束' },
};

const filterOptions = [
  { label: '全部', value: 'all' },
  { label: 'AI处理', value: 'active' },
  { label: '待接入', value: 'waiting' },
  { label: '已结束', value: 'closed' },
];

function ConversationList({
  conversations,
  selectedId,
  onSelect,
  loading = false,
  searchValue,
  onSearchChange,
  statusFilter = 'all',
  onStatusFilterChange,
  pagination,
  onPageChange,
}: ConversationListProps) {
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  const formatUserId = (id: string) => {
    if (id.startsWith('VIP')) return id;
    return `访客 #${id.slice(-4)}`;
  };

  return (
    <div className="h-full flex flex-col bg-white border-r border-gray-200">
      {/* Search */}
      <div className="p-4 border-b border-gray-200 space-y-2">
        <Input
          prefix={<SearchOutlined className="text-gray-400" />}
          placeholder="搜索会话ID或用户..."
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          allowClear
        />
        {onStatusFilterChange && (
          <Segmented
            block
            size="small"
            options={filterOptions}
            value={statusFilter}
            onChange={(v) => onStatusFilterChange(v as StatusFilter)}
          />
        )}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <Spin />
          </div>
        ) : (
          <List
            dataSource={conversations}
            renderItem={(item) => {
              const isSelected = selectedId === item.conversation_id;
              const status = statusConfig[item.status] || statusConfig.closed;

              return (
                <div
                  className={`
                    px-4 py-3 cursor-pointer transition-colors border-b border-gray-100
                    ${isSelected ? 'bg-blue-50 border-l-4 border-l-blue-600' : 'hover:bg-gray-50'}
                  `}
                  onClick={() => onSelect(item.conversation_id)}
                >
                  <div className="flex justify-between items-center mb-1">
                    <Text strong className="text-sm">
                      {formatUserId(item.user_external_id)}
                    </Text>
                    <Text type="secondary" className="text-xs">
                      {item.last_message_at
                        ? formatTime(item.last_message_at)
                        : formatTime(item.started_at)}
                    </Text>
                  </div>
                  <Text type="secondary" className="text-sm block truncate mb-2">
                    {item.last_message_preview || '暂无消息'}
                  </Text>
                  <Tag color={status.color} className="text-xs">
                    {status.text}
                  </Tag>
                </div>
              );
            }}
          />
        )}
      </div>

      {/* Pagination */}
      {pagination && onPageChange && pagination.total > pagination.size && (
        <div className="p-3 border-t border-gray-200 flex justify-center">
          <Pagination
            simple
            size="small"
            current={pagination.page}
            total={pagination.total}
            pageSize={pagination.size}
            onChange={onPageChange}
          />
        </div>
      )}
    </div>
  );
}

export default memo(ConversationList);

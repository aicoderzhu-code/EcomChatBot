'use client';

import { Table, Tag, Input, Select, Popconfirm, Typography, Space } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { KnowledgeDocument } from '@/types';

const { Link } = Typography;

interface DocumentListProps {
  documents: KnowledgeDocument[];
  loading?: boolean;
  searchValue: string;
  statusFilter: string;
  onSearchChange: (value: string) => void;
  onStatusFilterChange: (value: string) => void;
  onPreview: (doc: KnowledgeDocument) => void;
  onDelete: (id: string) => void;
  pagination: {
    current: number;
    pageSize: number;
    total: number;
    onChange: (page: number, pageSize: number) => void;
  };
}

const statusConfig: Record<string, { color: string; text: string }> = {
  completed: { color: 'green', text: '已完成' },
  processing: { color: 'blue', text: '处理中...' },
  pending: { color: 'default', text: '等待中' },
  failed: { color: 'red', text: '失败' },
};

const fileTypeColors: Record<string, string> = {
  pdf: 'red',
  docx: 'blue',
  doc: 'blue',
  md: 'purple',
  markdown: 'purple',
  txt: 'default',
};

export default function DocumentList({
  documents,
  loading = false,
  searchValue,
  statusFilter,
  onSearchChange,
  onStatusFilterChange,
  onPreview,
  onDelete,
  pagination,
}: DocumentListProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const columns: ColumnsType<KnowledgeDocument> = [
    {
      title: '文档名称',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'file_type',
      key: 'file_type',
      width: 100,
      render: (type: string) => (
        <Tag color={fileTypeColors[type.toLowerCase()] || 'default'}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: '切片数',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 80,
      render: (count: number, record) =>
        record.status === 'completed' ? count : '--',
    },
    {
      title: '上传时间',
      dataIndex: 'uploaded_at',
      key: 'uploaded_at',
      width: 160,
      render: (date: string) => formatDate(date),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = statusConfig[status] || statusConfig.pending;
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => {
        if (record.status === 'processing') {
          return <span className="text-gray-400">处理中</span>;
        }
        return (
          <Space>
            <Link onClick={() => onPreview(record)}>预览</Link>
            <Popconfirm
              title="确认删除"
              description="删除后无法恢复，确定要删除吗？"
              onConfirm={() => onDelete(record.knowledge_id)}
              okText="确定"
              cancelText="取消"
            >
              <Link className="text-red-500 hover:text-red-400">删除</Link>
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <Input
          prefix={<SearchOutlined className="text-gray-400" />}
          placeholder="搜索文档名称..."
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          style={{ width: 300 }}
          allowClear
        />
        <Select
          value={statusFilter}
          onChange={onStatusFilterChange}
          style={{ width: 150 }}
          options={[
            { value: '', label: '所有状态' },
            { value: 'completed', label: '处理完成' },
            { value: 'processing', label: '处理中' },
            { value: 'failed', label: '失败' },
          ]}
        />
      </div>

      {/* Table */}
      <Table
        columns={columns}
        dataSource={documents}
        rowKey="knowledge_id"
        loading={loading}
        pagination={{
          ...pagination,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
      />
    </div>
  );
}

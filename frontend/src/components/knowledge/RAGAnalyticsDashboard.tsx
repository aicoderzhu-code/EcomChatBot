'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Select, Space, Empty } from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined,
  SearchOutlined, TrophyOutlined, WarningOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  ragAnalyticsApi,
  RetrievalMetrics,
  FailedQuery,
  KnowledgeEffectiveness,
} from '@/lib/api/ragAnalytics';

export default function RAGAnalyticsDashboard() {
  const [metrics, setMetrics] = useState<RetrievalMetrics | null>(null);
  const [failedQueries, setFailedQueries] = useState<FailedQuery[]>([]);
  const [effectiveness, setEffectiveness] = useState<KnowledgeEffectiveness[]>([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [metricsResp, failedResp, effectResp] = await Promise.all([
        ragAnalyticsApi.getMetrics(days),
        ragAnalyticsApi.getFailedQueries(20),
        ragAnalyticsApi.getKnowledgeEffectiveness(20),
      ]);
      if (metricsResp.success) setMetrics(metricsResp.data);
      if (failedResp.success) setFailedQueries(failedResp.data || []);
      if (effectResp.success) setEffectiveness(effectResp.data || []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const failedColumns: ColumnsType<FailedQuery> = [
    { title: '查询内容', dataIndex: 'query', ellipsis: true },
    { title: '次数', dataIndex: 'count', width: 80, sorter: (a, b) => a.count - b.count },
    {
      title: '平均分数',
      dataIndex: 'avg_score',
      width: 100,
      render: (v: number) => <Tag color={v < 0.3 ? 'red' : 'orange'}>{v.toFixed(3)}</Tag>,
    },
    {
      title: '最近查询',
      dataIndex: 'last_queried',
      width: 160,
      render: (v: string | null) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
  ];

  const effectColumns: ColumnsType<KnowledgeEffectiveness> = [
    { title: '知识标题', dataIndex: 'title', ellipsis: true },
    { title: '使用次数', dataIndex: 'use_count', width: 90, sorter: (a, b) => a.use_count - b.use_count },
    {
      title: '平均分数',
      dataIndex: 'avg_score',
      width: 100,
      render: (v: number) => <Tag color={v >= 0.7 ? 'green' : v >= 0.5 ? 'orange' : 'red'}>{v.toFixed(3)}</Tag>,
    },
    {
      title: '有用率',
      dataIndex: 'helpful_rate',
      width: 90,
      render: (v: number | null) => v !== null ? `${v}%` : '-',
    },
    {
      title: '反馈',
      width: 120,
      render: (_, r) => (
        <Space size={4}>
          <span style={{ color: '#52c41a' }}><CheckCircleOutlined /> {r.helpful_count}</span>
          <span style={{ color: '#ff4d4f' }}><CloseCircleOutlined /> {r.unhelpful_count}</span>
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>检索效果分析</h3>
        <Select
          value={days}
          onChange={setDays}
          options={[
            { label: '近 7 天', value: 7 },
            { label: '近 30 天', value: 30 },
            { label: '近 90 天', value: 90 },
          ]}
          style={{ width: 120 }}
        />
      </div>

      {/* 核心指标 */}
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="总查询数"
              value={metrics?.total_queries || 0}
              prefix={<SearchOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="命中率"
              value={metrics?.hit_rate || 0}
              suffix="%"
              prefix={<TrophyOutlined />}
              valueStyle={{ color: (metrics?.hit_rate || 0) >= 70 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="平均匹配分数"
              value={metrics?.avg_match_score || 0}
              precision={3}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="有用反馈"
              value={metrics?.helpful_count || 0}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              suffix={
                <span style={{ fontSize: 14, color: '#999' }}>
                  / {(metrics?.helpful_count || 0) + (metrics?.unhelpful_count || 0)}
                </span>
              }
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* 失败查询 */}
        <Col xs={24} lg={12}>
          <Card
            title={<><WarningOutlined style={{ color: '#faad14' }} /> 低匹配查询</>}
            size="small"
          >
            {failedQueries.length > 0 ? (
              <Table
                columns={failedColumns}
                dataSource={failedQueries}
                rowKey="query"
                size="small"
                pagination={{ pageSize: 5 }}
                loading={loading}
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>

        {/* 知识效果排名 */}
        <Col xs={24} lg={12}>
          <Card
            title={<><TrophyOutlined style={{ color: '#1890ff' }} /> 知识效果排名</>}
            size="small"
          >
            {effectiveness.length > 0 ? (
              <Table
                columns={effectColumns}
                dataSource={effectiveness}
                rowKey="knowledge_id"
                size="small"
                pagination={{ pageSize: 5 }}
                loading={loading}
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

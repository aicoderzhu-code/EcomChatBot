'use client';

import { useState, useEffect } from 'react';
import { Row, Col, Spin, message, Card, Empty } from 'antd';
import {
  StatCard,
  TrendChart,
  RecentConversations,
} from '@/components/dashboard';
import { dashboardApi, DashboardSummary, HourlyTrend } from '@/lib/api/dashboard';
import { Conversation } from '@/types';

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardSummary | null>(null);
  const [trendData, setTrendData] = useState<Array<{ date: string; value: number }>>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);

        // Fetch dashboard data in parallel
        const [summaryRes, trendRes, convRes] = await Promise.all([
          dashboardApi.getSummary('24h').catch(() => ({ success: false, data: null })),
          dashboardApi.getHourlyTrend(24).catch(() => ({ success: false, data: [] })),
          dashboardApi.getRecentConversations(10).catch(() => ({ success: false, data: null })),
        ]);

        // Set stats
        if (summaryRes.success && summaryRes.data) {
          setStats(summaryRes.data);
        }

        // Transform hourly trend data
        if (trendRes.success && trendRes.data) {
          const transformed = (trendRes.data as HourlyTrend[]).map((item) => ({
            date: item.hour,
            value: item.count,
          }));
          setTrendData(transformed);
        }

        // Set conversations
        if (convRes.success && convRes.data) {
          setConversations(convRes.data.items || []);
        }
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
        message.error('加载数据失败');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats Cards - First Row */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <StatCard
            title="今日对话总数"
            value={stats?.total_conversations?.toLocaleString() || '0'}
            change={stats?.conversation_change || 0}
          />
        </Col>
        <Col xs={24} sm={8}>
          <StatCard
            title="活跃会话数"
            value={stats?.active_conversations?.toLocaleString() || '0'}
            suffix={`已完成: ${stats?.completed_conversations?.toLocaleString() || 0}`}
          />
        </Col>
        <Col xs={24} sm={8}>
          <StatCard
            title="消息总数"
            value={stats?.total_messages?.toLocaleString() || '0'}
            change={stats?.message_change || 0}
          />
        </Col>
      </Row>

      {/* Stats Cards - Second Row */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12}>
          <StatCard
            title="平均响应时间"
            value={`${(stats?.avg_response_time || 0).toFixed(2)}s`}
          />
        </Col>
        <Col xs={24} sm={12}>
          <StatCard
            title="平均满意度"
            value={`${((stats?.satisfaction_score || 0) * 20).toFixed(1)}%`}
            suffix={`评分: ${(stats?.satisfaction_score || 0).toFixed(1)}/5`}
          />
        </Col>
      </Row>

      {/* Trend Chart */}
      <Row gutter={[16, 16]}>
        <Col xs={24}>
          {trendData.length > 0 ? (
            <TrendChart data={trendData} title="24小时对话趋势" />
          ) : (
            <Card>
              <Empty description="暂无趋势数据" />
            </Card>
          )}
        </Col>
      </Row>

      {/* Recent Conversations */}
      <RecentConversations conversations={conversations} />
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { Alert, Button, Card, Radio, Tag, Typography } from 'antd';
import Skeleton from '@/components/ui/Loading/Skeleton';
import { subscriptionApi, SubscriptionStatus } from '@/lib/api/subscription';
import QuotaUsagePanel from './QuotaUsagePanel';

const { Title, Text } = Typography;

const PLAN_PRICES = [
  { key: 'monthly',     name: '月付版',  price: 199,  days: 30 },
  { key: 'quarterly',   name: '季付版',  price: 499,  days: 90 },
  { key: 'semi_annual', name: '半年付',  price: 899,  days: 180 },
  { key: 'annual',      name: '年付版',  price: 1699, days: 365 },
];

function statusTag(status: SubscriptionStatus['status']) {
  if (status === 'active') return <Tag color="green">有效</Tag>;
  if (status === 'grace')  return <Tag color="orange">宽限期</Tag>;
  return <Tag color="red">已过期</Tag>;
}

export default function SubscriptionPanel() {
  const [loading, setLoading] = useState(true);
  const [info, setInfo] = useState<SubscriptionStatus | null>(null);

  // 购买流程状态
  const [selectedPlan, setSelectedPlan] = useState<string>('monthly');
  const [ordering, setOrdering] = useState(false);

  useEffect(() => {
    subscriptionApi.getStatus()
      .then(res => { if (res.success && res.data) setInfo(res.data); })
      .finally(() => setLoading(false));
  }, []);

  const handlePay = async () => {
    setOrdering(true);
    try {
      const res = await subscriptionApi.createOrder({
        plan_type: selectedPlan,
        subscription_type: 'new',
        payment_channel: 'alipay',
      });
      if (res.success && res.data?.pay_url) {
        // 跳转到支付宝收银台
        window.location.href = res.data.pay_url;
      }
    } catch (e) {
      console.error(e);
    } finally {
      setOrdering(false);
    }
  };

  const selectedPlanInfo = PLAN_PRICES.find(p => p.key === selectedPlan);

  return (
    <>
    <QuotaUsagePanel />
    <Card>
      <Title level={5} className="mb-4">订阅管理</Title>
      {loading ? (
        <div className="space-y-4 py-2">
          <Skeleton variant="text" width="40%" />
          <Skeleton variant="rectangular" height={60} />
          <Skeleton variant="text" width="30%" className="mt-4" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} variant="rectangular" height={80} />
            ))}
          </div>
          <Skeleton variant="rectangular" height={40} className="mt-4" />
        </div>
      ) : (
      <div className="animate-fade-in">
        {/* 当前订阅状态 */}
        {info && (
          <div className="mb-6 space-y-2">
            <div className="flex items-center gap-3">
              <Text type="secondary">当前套餐：</Text>
              <Text strong>{info.plan_name}</Text>
              {statusTag(info.status)}
            </div>
            {info.expire_at && (
              <div>
                <Text type="secondary">到期时间：</Text>
                <Text>{new Date(info.expire_at).toLocaleDateString('zh-CN')}</Text>
              </div>
            )}
            {info.is_in_grace && info.grace_period_end && (
              <Alert
                type="warning"
                showIcon
                message={`订阅已过期，宽限期截止：${new Date(info.grace_period_end).toLocaleDateString('zh-CN')}`}
              />
            )}
            {info.status === 'expired' && !info.is_in_grace && (
              <Alert type="error" showIcon message="订阅已过期，请续费" />
            )}
          </div>
        )}

        {/* 套餐选择 */}
        <Title level={5} className="mb-3">选择套餐</Title>
        <Radio.Group
          value={selectedPlan}
          onChange={e => setSelectedPlan(e.target.value)}
          className="mb-4 w-full"
        >
          <div className="grid grid-cols-2 gap-2">
            {PLAN_PRICES.map(plan => (
              <Radio.Button
                key={plan.key}
                value={plan.key}
                className="text-center"
                style={{ height: 'auto', padding: '8px 12px' }}
              >
                <div className="font-medium">{plan.name}</div>
                <div className="text-sm text-gray-500">¥{plan.price} / {plan.days}天</div>
              </Radio.Button>
            ))}
          </div>
        </Radio.Group>

        {/* 支付按钮 */}
        <Button
          type="primary"
          size="large"
          block
          loading={ordering}
          onClick={handlePay}
          disabled={!selectedPlan}
        >
          支付宝付款 ¥{selectedPlanInfo?.price ?? '--'}
        </Button>
      </div>
      )}
    </Card>
    </>
  );
}

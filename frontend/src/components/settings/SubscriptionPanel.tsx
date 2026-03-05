'use client';

import { useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { Alert, Button, Card, Modal, Radio, Spin, Tag, Typography } from 'antd';
import { subscriptionApi, SubscriptionStatus, CreateOrderResponse } from '@/lib/api/subscription';

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
  const [paymentChannel, setPaymentChannel] = useState<'alipay' | 'wechat'>('alipay');
  const [ordering, setOrdering] = useState(false);
  const [order, setOrder] = useState<CreateOrderResponse | null>(null);
  const [qrModalOpen, setQrModalOpen] = useState(false);
  const [pollStatus, setPollStatus] = useState<'polling' | 'paid' | 'timeout' | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollCountRef = useRef(0);

  useEffect(() => {
    subscriptionApi.getStatus()
      .then(res => { if (res.success && res.data) setInfo(res.data); })
      .finally(() => setLoading(false));
  }, []);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const startPolling = (orderNumber: string) => {
    pollCountRef.current = 0;
    setPollStatus('polling');
    pollRef.current = setInterval(async () => {
      pollCountRef.current += 1;
      // 超时：10 分钟 = 200 次 × 3 秒
      if (pollCountRef.current > 200) {
        stopPolling();
        setPollStatus('timeout');
        return;
      }
      try {
        const res = await subscriptionApi.syncOrder(orderNumber);
        if (res.success && res.data?.order?.status === 'paid') {
          stopPolling();
          setPollStatus('paid');
          // 刷新订阅状态
          const statusRes = await subscriptionApi.getStatus();
          if (statusRes.success && statusRes.data) setInfo(statusRes.data);
        }
      } catch {
        // 忽略轮询中的网络错误
      }
    }, 3000);
  };

  const handlePay = async () => {
    setOrdering(true);
    try {
      const res = await subscriptionApi.createOrder({
        plan_type: selectedPlan,
        subscription_type: 'new',
        payment_channel: paymentChannel,
      });
      if (res.success && res.data) {
        setOrder(res.data);
        setQrModalOpen(true);
        startPolling(res.data.order_number);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setOrdering(false);
    }
  };

  const handleCloseModal = () => {
    stopPolling();
    setQrModalOpen(false);
    setOrder(null);
    setPollStatus(null);
  };

  const selectedPlanInfo = PLAN_PRICES.find(p => p.key === selectedPlan);

  return (
    <Card>
      <Title level={5} className="mb-4">订阅管理</Title>
      <Spin spinning={loading}>
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

        {/* 支付方式选择 */}
        <Title level={5} className="mb-3">支付方式</Title>
        <Radio.Group
          value={paymentChannel}
          onChange={e => setPaymentChannel(e.target.value)}
          className="mb-4"
        >
          <Radio value="alipay">支付宝</Radio>
          <Radio value="wechat">微信支付</Radio>
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
          {paymentChannel === 'alipay' ? '支付宝' : '微信'}扫码支付 ¥{selectedPlanInfo?.price ?? '--'}
        </Button>
      </Spin>

      {/* 二维码弹窗 */}
      <Modal
        title={`${paymentChannel === 'alipay' ? '支付宝' : '微信'}扫码支付 - ${selectedPlanInfo?.name}`}
        open={qrModalOpen}
        onCancel={handleCloseModal}
        footer={null}
        centered
        width={360}
      >
        {pollStatus === 'paid' ? (
          <div className="text-center py-8">
            <div className="text-5xl mb-4">✅</div>
            <Text strong className="text-lg">支付成功！</Text>
            <div className="mt-2 text-gray-500">订阅已激活</div>
            <Button type="primary" className="mt-4" onClick={handleCloseModal}>
              关闭
            </Button>
          </div>
        ) : pollStatus === 'timeout' ? (
          <div className="text-center py-8">
            <Alert type="warning" showIcon message="支付超时，请重新发起支付" />
            <Button className="mt-4" onClick={handleCloseModal}>关闭</Button>
          </div>
        ) : (
          <div className="text-center">
            {order?.qr_code_url ? (
              <>
                <Image
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(order.qr_code_url)}`}
                  alt={`${paymentChannel === 'alipay' ? '支付宝' : '微信'}支付二维码`}
                  className="mx-auto mb-3"
                  width={200}
                  height={200}
                  unoptimized
                />
                <div className="text-gray-500 text-sm mb-2">
                  请使用{paymentChannel === 'alipay' ? '支付宝' : '微信"扫一扫"'}扫码支付
                </div>
                <Text strong className="text-lg text-red-500">
                  ¥{order.amount}
                </Text>
                <div className="mt-3 flex items-center justify-center gap-2 text-gray-400 text-sm">
                  <Spin size="small" />
                  <span>等待支付结果...</span>
                </div>
              </>
            ) : (
              <Spin tip="生成二维码中..." />
            )}
          </div>
        )}
      </Modal>
    </Card>
  );
}

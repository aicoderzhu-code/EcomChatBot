"""新增模型测试"""
from models.after_sale import AfterSaleRecord
from models.webhook_event import WebhookEvent


def test_after_sale_record_tablename():
    assert AfterSaleRecord.__tablename__ == "after_sale_records"


def test_after_sale_record_columns():
    columns = {c.name for c in AfterSaleRecord.__table__.columns}
    assert "platform_config_id" in columns
    assert "platform_aftersale_id" in columns
    assert "aftersale_type" in columns
    assert "refund_amount" in columns
    assert "tenant_id" in columns


def test_webhook_event_tablename():
    assert WebhookEvent.__tablename__ == "webhook_events"


def test_webhook_event_columns():
    columns = {c.name for c in WebhookEvent.__table__.columns}
    assert "event_id" in columns
    assert "platform_type" in columns
    assert "event_type" in columns
    assert "payload" in columns
    assert "status" in columns
    assert "retry_count" in columns

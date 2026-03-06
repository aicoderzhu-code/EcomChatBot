"""PlatformApp 模型导入测试"""
from models.platform_app import PlatformApp


def test_platform_app_tablename():
    assert PlatformApp.__tablename__ == "platform_apps"


def test_platform_app_has_required_columns():
    columns = {c.name for c in PlatformApp.__table__.columns}
    assert "platform_type" in columns
    assert "app_key" in columns
    assert "app_secret" in columns
    assert "callback_url" in columns
    assert "webhook_url" in columns
    assert "scopes" in columns
    assert "status" in columns
    assert "extra_config" in columns


def test_platform_app_repr():
    app = PlatformApp(platform_type="taobao", app_name="测试应用", app_key="k", app_secret="s")
    assert "taobao" in repr(app)

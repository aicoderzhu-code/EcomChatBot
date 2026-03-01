#!/usr/bin/env python3
"""测试 TOS 存储功能"""
import os
import sys

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 添加 backend 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# 设置必需的环境变量（如果未设置）
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://user:pass@localhost/db')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('JWT_SECRET', 'test-secret')

from services.storage.tos_backend import TosStorageBackend
from core.config import settings

def test_tos_connection():
    """测试 TOS 连接"""
    print("=" * 60)
    print("测试 TOS 存储连接")
    print("=" * 60)

    print(f"\n配置信息:")
    print(f"  Endpoint: {settings.tos_endpoint}")
    print(f"  Region: {settings.tos_region}")
    print(f"  Bucket: {settings.tos_bucket}")
    print(f"  Access Key: {settings.tos_access_key[:10]}...")

    try:
        print("\n初始化 TOS 客户端...")
        backend = TosStorageBackend()
        print("✅ TOS 客户端初始化成功")

        print("\n测试上传小文件...")
        test_data = b"Hello, TOS! This is a test file."
        test_key = "test/test_file.txt"

        backend.put_object(test_key, test_data, "text/plain")
        print(f"✅ 文件上传成功: {test_key}")

        print("\n生成预签名 URL...")
        url = backend.get_public_url(test_key)
        print(f"✅ 预签名 URL: {url[:80]}...")

        print("\n测试下载文件...")
        downloaded_data = backend.get_object(test_key)
        assert downloaded_data == test_data, "下载的数据与上传的数据不匹配"
        print("✅ 文件下载成功，数据一致")

        print("\n测试删除文件...")
        backend.delete_object(test_key)
        print(f"✅ 文件删除成功: {test_key}")

        print("\n" + "=" * 60)
        print("🎉 所有测试通过！TOS 存储功能正常")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_tos_connection()
    sys.exit(0 if success else 1)

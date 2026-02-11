#!/usr/bin/env python3
"""
简单的API测试脚本 - 使用标准库
"""
import urllib.request
import urllib.error
import json

def test_api():
    print("="*60)
    print("测试本地Docker API")
    print("="*60)
    print()
    
    # 测试不同的URL
    urls = [
        "http://127.0.0.1:8000/",
        "http://127.0.0.1:8000/health",
        "http://127.0.0.1:8000/api/v1/health",
    ]
    
    for url in urls:
        print(f"测试: {url}")
        try:
            # 创建请求，不使用代理
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)
            
            with urllib.request.urlopen(url, timeout=10) as response:
                status_code = response.status
                content = response.read().decode('utf-8')
                print(f"  ✅ 状态码: {status_code}")
                print(f"  响应: {content[:150]}")
        except urllib.error.HTTPError as e:
            print(f"  ❌ HTTP错误 {e.code}: {e.reason}")
            try:
                error_content = e.read().decode('utf-8')
                print(f"  响应: {error_content[:150]}")
            except:
                pass
        except urllib.error.URLError as e:
            print(f"  ❌ URL错误: {e.reason}")
        except Exception as e:
            print(f"  ❌ 其他错误: {e}")
        print()

if __name__ == "__main__":
    test_api()

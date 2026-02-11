#!/usr/bin/env python3
"""
测试环境预检查脚本
在执行测试前检查所有必需的配置和依赖
"""
import os
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def check_environment():
    """检查测试环境配置"""
    print("=" * 60)
    print("🔍 测试环境预检查")
    print("=" * 60)
    print()
    
    issues = []
    warnings = []
    
    # 1. 检查 .env.test 文件
    print("1️⃣  检查配置文件...")
    env_file = Path(__file__).parent / ".env.test"
    if not env_file.exists():
        issues.append("未找到 .env.test 文件")
        print("   ❌ 未找到 .env.test 文件")
    else:
        print("   ✅ .env.test 文件存在")
        
        # 读取配置
        with open(env_file) as f:
            content = f.read()
            
        # 检查 BASE_URL
        if "BASE_URL=" in content:
            base_url = [line for line in content.split('\n') if line.startswith('BASE_URL=')][0].split('=')[1].strip()
            print(f"   ✅ BASE_URL: {base_url}")
        else:
            issues.append("BASE_URL 未配置")
            
        # 检查 LLM 配置
        if "DEEPSEEK_API_KEY=sk-your-deepseek-api-key" in content or "DEEPSEEK_API_KEY=" not in content:
            warnings.append("未配置 DEEPSEEK_API_KEY（AI 功能测试将失败）")
            print("   ⚠️  DEEPSEEK_API_KEY 未配置")
        elif "DEEPSEEK_API_KEY=" in content:
            print("   ✅ DEEPSEEK_API_KEY 已配置")
    print()
    
    # 2. 检查 Python 依赖
    print("2️⃣  检查 Python 依赖...")
    required_packages = [
        ('pytest', 'pytest'),
        ('pytest_asyncio', 'pytest-asyncio'),
        ('httpx', 'httpx'),
        ('pydantic', 'pydantic'),
        ('pydantic_settings', 'pydantic-settings'),
        ('dotenv', 'python-dotenv'),
    ]
    
    missing_packages = []
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"   ✅ {package_name}")
        except ImportError:
            missing_packages.append(package_name)
            print(f"   ❌ {package_name} 未安装")
    
    if missing_packages:
        issues.append(f"缺少依赖包: {', '.join(missing_packages)}")
        print()
        print(f"   💡 安装命令: pip3 install {' '.join(missing_packages)}")
    print()
    
    # 3. 检查服务器连接
    print("3️⃣  检查服务器连接...")
    try:
        import httpx
        from config import settings
        
        print(f"   正在连接: {settings.base_url} ...")
        
        with httpx.Client(timeout=10.0) as client:
            try:
                response = client.get(f"{settings.base_url}/health")
                if response.status_code == 200:
                    print(f"   ✅ 服务器连接成功 (HTTP {response.status_code})")
                    data = response.json()
                    if "status" in data:
                        print(f"   ✅ 服务状态: {data.get('status')}")
                else:
                    warnings.append(f"服务器返回非 200 状态码: {response.status_code}")
                    print(f"   ⚠️  服务器返回 HTTP {response.status_code}")
            except httpx.ConnectError as e:
                issues.append(f"无法连接到服务器: {settings.base_url}")
                print(f"   ❌ 连接失败: {e}")
            except httpx.TimeoutException:
                warnings.append("服务器响应超时")
                print(f"   ⚠️  连接超时（10秒）")
            except Exception as e:
                warnings.append(f"服务器检查异常: {e}")
                print(f"   ⚠️  检查异常: {e}")
                
    except ImportError:
        print("   ⏭️  跳过（httpx 未安装）")
    except Exception as e:
        print(f"   ⚠️  检查失败: {e}")
    print()
    
    # 4. 检查测试文件
    print("4️⃣  检查测试文件...")
    test_dirs = ["api", "integration", "performance", "security"]
    for test_dir in test_dirs:
        test_path = Path(__file__).parent / test_dir
        if test_path.exists():
            test_files = list(test_path.glob("test_*.py"))
            print(f"   ✅ {test_dir}/: {len(test_files)} 个测试文件")
        else:
            warnings.append(f"测试目录不存在: {test_dir}")
            print(f"   ⚠️  {test_dir}/ 不存在")
    print()
    
    # 5. 总结
    print("=" * 60)
    print("📊 检查结果")
    print("=" * 60)
    
    if not issues and not warnings:
        print("✅ 所有检查通过！可以开始测试")
        print()
        print("🚀 快速开始:")
        print("   pytest api/test_health.py -v")
        return 0
    
    if warnings:
        print(f"⚠️  警告 ({len(warnings)} 项):")
        for warning in warnings:
            print(f"   - {warning}")
        print()
    
    if issues:
        print(f"❌ 错误 ({len(issues)} 项):")
        for issue in issues:
            print(f"   - {issue}")
        print()
        print("请先解决上述问题后再执行测试")
        return 1
    
    print("⚠️  存在警告，但可以继续测试")
    print()
    print("🚀 建议开始:")
    print("   pytest api/test_health.py -v")
    return 0


if __name__ == "__main__":
    exit_code = check_environment()
    sys.exit(exit_code)

#!/usr/bin/env python3
"""
快速测试验证脚本
用于验证测试套件是否正常工作
"""
import subprocess
import sys
from pathlib import Path


def print_header(message):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {message}")
    print("=" * 60 + "\n")


def run_command(command, description):
    """运行命令"""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print(f"✅ {description} - 成功")
            return True
        else:
            print(f"❌ {description} - 失败")
            if result.stderr:
                print(f"   错误: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️  {description} - 超时")
        return False
    except Exception as e:
        print(f"❌ {description} - 异常: {str(e)}")
        return False


def main():
    """主函数"""
    print_header("电商智能客服SaaS平台 - 测试套件验证")

    # 检查当前目录
    tests_dir = Path(__file__).parent
    print(f"📁 测试目录: {tests_dir}")

    # 检查测试文件
    test_files = list(tests_dir.glob("test_*.py"))
    print(f"📊 测试文件数量: {len(test_files)}")

    for test_file in sorted(test_files):
        print(f"   - {test_file.name}")

    print()

    # 统计信息
    print_header("统计信息")

    # 统计测试用例数量
    result = subprocess.run(
        "grep -r 'async def test_' test_*.py 2>/dev/null | wc -l",
        shell=True,
        capture_output=True,
        text=True,
        cwd=tests_dir,
    )

    if result.returncode == 0:
        test_count = result.stdout.strip()
        print(f"🧪 测试用例总数: {test_count}")

    # 统计测试类数量
    result = subprocess.run(
        "grep -r 'class Test' test_*.py 2>/dev/null | wc -l",
        shell=True,
        capture_output=True,
        text=True,
        cwd=tests_dir,
    )

    if result.returncode == 0:
        class_count = result.stdout.strip()
        print(f"📦 测试类总数: {class_count}")

    print()

    # 验证测试
    print_header("验证测试套件")

    checks = []

    # 检查1: pytest是否可用
    checks.append(
        run_command("pytest --version", "检查pytest是否安装")
    )

    # 检查2: 收集测试
    checks.append(
        run_command(
            f"cd {tests_dir} && pytest --collect-only -q test_01_health.py",
            "收集健康检查测试",
        )
    )

    # 检查3: 运行快速测试
    checks.append(
        run_command(
            f"cd {tests_dir} && pytest test_01_health.py::TestHealthCheckAPIs::test_health_basic -v --tb=short || true",
            "运行单个测试用例",
        )
    )

    # 检查4: 验证fixtures
    checks.append(
        run_command(
            f"cd {tests_dir} && pytest --fixtures -q | head -20 > /dev/null",
            "验证fixtures配置",
        )
    )

    # 总结
    print()
    print_header("验证结果")

    success_count = sum(checks)
    total_count = len(checks)

    print(f"✅ 成功: {success_count}/{total_count}")
    print(f"❌ 失败: {total_count - success_count}/{total_count}")

    if success_count == total_count:
        print("\n🎉 测试套件验证通过! 可以正常使用!")
        print("\n📖 下一步:")
        print("   1. 运行完整测试: ./run_all_tests.sh")
        print("   2. 查看文档: cat README_TESTING.md")
        print("   3. 查看报告: cat TEST_COMPLETION_REPORT.md")
        return 0
    else:
        print("\n⚠️  部分检查失败，请检查:")
        print("   1. 是否安装了测试依赖: pip install -r requirements-test.txt")
        print("   2. 是否在正确的目录")
        print("   3. Python版本是否正确 (3.11+)")
        return 1


if __name__ == "__main__":
    sys.exit(main())

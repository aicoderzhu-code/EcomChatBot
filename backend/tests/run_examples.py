"""
测试套件 - 示例运行脚本
演示如何运行各种测试场景
"""
import subprocess
import sys


def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def run_test(description, command):
    """运行测试并显示结果"""
    print(f"📝 {description}")
    print(f"💻 命令: {command}\n")
    
    result = subprocess.run(command, shell=True, cwd=".")
    
    if result.returncode == 0:
        print(f"✅ {description} - 通过\n")
    else:
        print(f"❌ {description} - 失败\n")
    
    return result.returncode == 0


def main():
    """主函数"""
    print_section("电商智能客服SaaS平台 - 测试示例")

    examples = [
        ("运行健康检查测试", "pytest test_01_health.py -v"),
        ("运行租户管理测试", "pytest test_03_tenant.py -v"),
        ("运行支付管理测试", "pytest test_07_payment.py -v"),
        ("运行E2E测试", "pytest test_e2e.py -v"),
        ("运行冒烟测试", "pytest -m smoke -v"),
        ("运行快速测试", "pytest -m fast -v"),
        ("生成覆盖率报告", "pytest test_01_health.py --cov=api --cov-report=term"),
    ]

    print("以下是一些测试运行示例:\n")

    for i, (desc, cmd) in enumerate(examples, 1):
        print(f"{i}. {desc}")
        print(f"   命令: {cmd}\n")

    print("\n" + "=" * 70)
    print("  选择一个示例运行，或使用 ./run_all_tests.sh 运行所有测试")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

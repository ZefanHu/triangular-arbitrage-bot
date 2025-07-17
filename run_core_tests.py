#!/usr/bin/env python3
"""
Core功能快速测试脚本

这是一个简化的测试入口，用于快速验证所有core模块的功能
"""

import asyncio
import sys
import os
from test_core_comprehensive import CoreTester


async def quick_test():
    """快速测试 - 运行核心功能验证"""
    print("🚀 Core模块快速测试")
    print("=" * 50)
    
    tester = CoreTester()
    
    # 运行关键测试
    critical_tests = [
        ("配置验证", tester.test_config_manager),
        ("OKX API连接", tester.test_okx_api),
        ("数据采集", tester.test_data_collector),
        ("套利计算", tester.test_arbitrage_engine),
    ]
    
    passed = 0
    total = len(critical_tests)
    
    for test_name, test_func in critical_tests:
        print(f"\n🔍 测试: {test_name}")
        try:
            result = await test_func()
            if result:
                print(f"✅ {test_name} - 通过")
                passed += 1
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"💥 {test_name} - 异常: {e}")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有关键功能正常!")
        return True
    else:
        print("⚠️ 部分功能存在问题，建议运行完整测试")
        return False


async def full_test():
    """完整测试"""
    print("🔧 Core模块完整测试")
    tester = CoreTester()
    return await tester.run_all_tests()


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        # 完整测试
        asyncio.run(full_test())
    else:
        # 快速测试
        result = asyncio.run(quick_test())
        if not result:
            print("\n运行 'python run_core_tests.py --full' 获取详细测试报告")


if __name__ == "__main__":
    main()
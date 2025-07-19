#!/usr/bin/env python3
"""
Core功能快速测试脚本

这是一个简化的测试入口，用于快速验证所有core模块的功能
"""

import asyncio
import sys
import os

# Add parent directory to path to access project modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_core_comprehensive import CoreTester


async def quick_test():
    """快速测试 - 运行核心功能验证"""
    print("🚀 Core模块快速测试")
    print("=" * 50)
    print("📋 测试范围: 配置验证、API连接、数据采集、套利计算")
    print("🎯 目标: 快速验证核心功能是否正常运行")
    print("⏱️  预计时间: 30-60秒\n")
    
    # 显示测试环境信息
    import time
    import os
    print("🔍 测试环境信息:")
    print(f"  ⏰ 开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  📂 工作目录: {os.getcwd()}")
    print(f"  🐍 Python版本: {os.sys.version.split()[0]}")
    
    # 检查关键文件 (修正路径为从项目根目录查找)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_files = [
        os.path.join(project_root, 'config', 'settings.ini'),
        os.path.join(project_root, 'config', 'secrets.ini'),
        os.path.join(project_root, 'config', 'secrets.ini.example')
    ]
    print(f"  📁 配置文件检查:")
    for file_path in config_files:
        exists = os.path.exists(file_path)
        relative_path = os.path.relpath(file_path, project_root)
        print(f"    {relative_path}: {'✅ 存在' if exists else '❌ 缺失'}")
    
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
    test_results = []
    
    print(f"\n🔬 开始执行 {total} 项核心测试...")
    print("=" * 60)
    
    overall_start_time = time.time()
    
    for i, (test_name, test_func) in enumerate(critical_tests, 1):
        print(f"\n📍 [{i}/{total}] 测试: {test_name}")
        print("-" * 40)
        
        test_start_time = time.time()
        try:
            result = await test_func()
            test_duration = time.time() - test_start_time
            
            if result:
                print(f"✅ {test_name} - 通过 (耗时: {test_duration:.2f}s)")
                passed += 1
                test_results.append({'name': test_name, 'status': 'passed', 'duration': test_duration})
            else:
                print(f"❌ {test_name} - 失败 (耗时: {test_duration:.2f}s)")
                test_results.append({'name': test_name, 'status': 'failed', 'duration': test_duration})
        except Exception as e:
            test_duration = time.time() - test_start_time
            print(f"💥 {test_name} - 异常 (耗时: {test_duration:.2f}s)")
            print(f"   错误详情: {str(e)}")
            test_results.append({'name': test_name, 'status': 'error', 'duration': test_duration, 'error': str(e)})
    
    overall_duration = time.time() - overall_start_time
    
    # 显示详细测试结果
    print(f"\n{'='*60}")
    print(f"📊 Core模块快速测试结果")
    print(f"{'='*60}")
    print(f"⏱️  总测试时间: {overall_duration:.2f}秒")
    print(f"📈 通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"📋 详细结果:")
    
    for result in test_results:
        status_icon = {"passed": "✅", "failed": "❌", "error": "💥"}.get(result['status'], "❓")
        print(f"  {status_icon} {result['name']}: {result['status']} ({result['duration']:.2f}s)")
        if 'error' in result:
            print(f"     💬 错误: {result['error']}")
    
    # 性能分析
    if test_results:
        avg_duration = sum(r['duration'] for r in test_results) / len(test_results)
        slowest_test = max(test_results, key=lambda x: x['duration'])
        print(f"\n⚡ 性能分析:")
        print(f"  📊 平均测试时间: {avg_duration:.2f}s")
        print(f"  🐌 最慢测试: {slowest_test['name']} ({slowest_test['duration']:.2f}s)")
    
    if passed == total:
        print(f"\n🎉 所有关键功能正常!")
        print(f"✨ 系统状态: 健康")
        return True
    else:
        failed_count = total - passed
        print(f"\n⚠️ {failed_count} 项功能存在问题")
        print(f"🔧 建议: 运行完整测试获取详细诊断信息")
        print(f"💡 命令: python run_core_tests.py --full")
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
#!/usr/bin/env python3
"""
简化的测试运行脚本
"""

import subprocess
import sys
import os


def run_tests():
    """运行清理后的测试"""
    print("🧪 运行三角套利机器人的核心测试...")
    
    # 确保在项目根目录
    os.chdir('/home/huzefan/triangular-arbitrage-bot')
    
    # 运行核心测试（排除集成测试）
    test_commands = [
        "python -m pytest tests/test_arbitrage_engine.py -v -k 'not integration' --tb=short",
        "python -m pytest tests/test_risk_manager.py -v -k 'not integration' --tb=short",
        "python -m pytest tests/test_trade_executor.py -v -k 'not integration' --tb=short",
    ]
    
    all_passed = True
    
    for cmd in test_commands:
        print(f"\n{'='*60}")
        print(f"运行: {cmd}")
        print(f"{'='*60}")
        
        result = subprocess.run(cmd, shell=True, capture_output=False)
        
        if result.returncode != 0:
            all_passed = False
            print(f"❌ 测试失败: {cmd}")
        else:
            print(f"✅ 测试通过: {cmd}")
    
    if all_passed:
        print("\n🎉 所有核心测试都通过了！")
    else:
        print("\n⚠️  部分测试失败，请检查上面的错误信息")
        
    return all_passed


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
运行数据层集成测试的便捷脚本

使用说明：
python run_integration_tests.py

注意：
- 需要配置正确的API凭据（模拟盘）
- 需要网络连接
- 测试可能需要较长时间
"""

import sys
import os
import logging
import asyncio
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.test_data_integration import run_integration_tests


def setup_logging():
    """设置日志配置"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'logs/integration_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )


def check_environment():
    """检查测试环境"""
    logger = logging.getLogger(__name__)
    
    # 检查配置文件
    config_files = [
        'config/secrets.ini',
        'config/settings.ini'
    ]
    
    for config_file in config_files:
        if not os.path.exists(config_file):
            logger.error(f"配置文件不存在: {config_file}")
            return False
    
    # 检查日志目录
    if not os.path.exists('logs'):
        os.makedirs('logs')
        logger.info("创建日志目录")
    
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("数据层集成测试")
    print("=" * 60)
    
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 检查环境
    if not check_environment():
        logger.error("环境检查失败")
        return 1
    
    logger.info("开始运行数据层集成测试...")
    logger.info("使用模拟盘API进行测试")
    
    try:
        # 运行集成测试
        success = run_integration_tests()
        
        if success:
            logger.info("✅ 所有集成测试通过！")
            print("\n" + "=" * 60)
            print("✅ 测试结果：全部通过")
            print("=" * 60)
            return 0
        else:
            logger.error("❌ 部分测试失败")
            print("\n" + "=" * 60)
            print("❌ 测试结果：存在失败")
            print("=" * 60)
            return 1
            
    except KeyboardInterrupt:
        logger.info("用户中断测试")
        return 1
    except Exception as e:
        logger.error(f"测试运行异常: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
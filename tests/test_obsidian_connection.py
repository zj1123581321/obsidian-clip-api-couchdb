"""
测试 Obsidian REST API 连接

这个测试文件用于验证当前配置文件中的 Obsidian REST API 连接是否正常工作。
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import config
from app.services.obsidian_rest_api import ObsidianRestAPIService


class ObsidianConnectionTester:
    """Obsidian 连接测试类"""
    
    def __init__(self):
        self.service = ObsidianRestAPIService()
    
    def print_config(self):
        """打印当前配置"""
        print("=== 当前配置信息 ===")
        print(f"存储方式: {config.storage_method}")
        print(f"Obsidian API URL: {config.get('obsidian_api.url', '未配置')}")
        print(f"API Key: {'已配置' if config.get('obsidian_api.api_key') else '未配置'}")
        print(f"超时时间: {config.get('obsidian_api.timeout', 30)} 秒")
        print(f"重试次数: {config.get('obsidian_api.retry_count', 3)}")
        print(f"文件保存路径: {config.get('obsidian.clippings_path', 'Clippings')}")
        print(f"日期文件夹: {'启用' if config.get('obsidian.date_folder', True) else '禁用'}")
        print()
    
    async def test_basic_connection(self):
        """测试基本连接"""
        print("=== 测试基本连接 ===")
        try:
            connection_info = await self.service.test_connection()
            
            if connection_info['status'] == 'connected':
                print("[成功] 连接成功！")
                print(f"服务: {connection_info.get('service', '未知')}")
                print(f"版本: {connection_info.get('version', '未知')}")
                print(f"认证状态: {'已认证' if connection_info.get('authenticated') else '未认证'}")
                print(f"请求URL: {connection_info.get('url', '未知')}")
                return True
            else:
                print("[失败] 连接失败")
                print(f"状态: {connection_info['status']}")
                print(f"错误: {connection_info.get('error', '未知错误')}")
                print(f"请求URL: {connection_info.get('url', '未知')}")
                return False
                
        except Exception as e:
            print(f"[异常] 连接异常: {str(e)}")
            return False
        finally:
            print()
    
    async def test_health_check(self):
        """测试健康检查"""
        print("=== 测试健康检查 ===")
        try:
            is_healthy = await self.service.health_check()
            if is_healthy:
                print("[成功] 健康检查通过")
                return True
            else:
                print("[失败] 健康检查失败")
                return False
        except Exception as e:
            print(f"[异常] 健康检查异常: {str(e)}")
            return False
        finally:
            print()
    
    def test_file_path_generation(self):
        """测试文件路径生成"""
        print("=== 测试文件路径生成 ===")
        try:
            test_titles = [
                "这是一个测试标题",
                "Test Article with English",
                "包含特殊字符<>:\"/\\|?*的标题",
                "很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长的标题",
                ""  # 空标题
            ]
            
            for i, title in enumerate(test_titles, 1):
                file_path = self.service.generate_file_path(title)
                print(f"{i}. 标题: '{title}'")
                print(f"   路径: {file_path}")
                print()
            
            return True
        except Exception as e:
            print(f"[失败] 文件路径生成失败: {str(e)}")
            return False
    
    async def test_create_test_document(self):
        """测试创建文档（如果连接成功）"""
        print("=== 测试创建文档 ===")
        print("注意: 此测试将在 Obsidian 中创建一个测试文件")
        
        # 询问用户是否继续
        try:
            user_input = input("是否继续创建测试文档？(y/N): ").strip().lower()
            if user_input != 'y':
                print("已跳过文档创建测试")
                return True
        except (EOFError, KeyboardInterrupt):
            print("\n已跳过文档创建测试")
            return True
        
        try:
            # 创建测试文档
            test_content = """---
url: https://example.com/test
title: Obsidian REST API 连接测试
description: 这是一个用于测试 REST API 连接的文档
author: 系统测试
published: 
created: 2024-03-06 15:30
---

# Obsidian REST API 连接测试

这是一个由 Obsidian 剪藏 API 服务创建的测试文档。

## 测试信息

- 测试时间: 2024-03-06 15:30
- 服务版本: v1.0.0
- 连接状态: 正常

## 功能验证

- ✅ 网络连接
- ✅ API 认证
- ✅ 文件创建
- ✅ 路径生成

如果您看到这个文档，说明 REST API 连接工作正常！

---
*此文档由系统自动生成，可以安全删除*
"""
            
            file_path = await self.service.save_document(
                "Obsidian REST API 连接测试",
                test_content,
                "https://example.com/test"
            )
            
            print(f"[成功] 文档创建成功！")
            print(f"文件路径: {file_path}")
            return True
            
        except Exception as e:
            print(f"[失败] 文档创建失败: {str(e)}")
            return False
        finally:
            print()
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("开始 Obsidian REST API 连接测试")
        print("=" * 50)
        print()
        
        # 打印配置
        self.print_config()
        
        # 测试结果
        results = []
        
        # 1. 测试文件路径生成（不需要网络连接）
        results.append(("文件路径生成", self.test_file_path_generation()))
        
        # 2. 测试基本连接
        connection_ok = await self.test_basic_connection()
        results.append(("基本连接", connection_ok))
        
        # 3. 测试健康检查
        if connection_ok:
            health_ok = await self.test_health_check()
            results.append(("健康检查", health_ok))
            
            # 4. 测试文档创建（可选）
            create_ok = await self.test_create_test_document()
            results.append(("文档创建", create_ok))
        
        # 输出测试结果
        print("=" * 50)
        print("测试结果汇总")
        print("=" * 50)
        
        all_passed = True
        for test_name, passed in results:
            status = "通过" if passed else "失败"
            print(f"{test_name:15} {status}")
            if not passed:
                all_passed = False
        
        print("=" * 50)
        if all_passed:
            print("所有测试通过！Obsidian REST API 连接工作正常。")
        else:
            print("部分测试失败，请检查配置和 Obsidian 服务状态。")
        
        print("\n提示:")
        print("- 确保 Obsidian 正在运行")
        print("- 确保 Local REST API 插件已启用")
        print("- 检查 API Key 是否正确")
        print("- 检查 URL 和端口配置")


async def main():
    """主函数"""
    tester = ObsidianConnectionTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    # 运行测试
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户取消测试")
    except Exception as e:
        print(f"\n\n测试程序异常: {str(e)}")
        import traceback
        traceback.print_exc()
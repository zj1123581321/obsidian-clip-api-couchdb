import os
import sys
import unittest

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.markdown_converter import markdown_converter

class TestMarkdownConverter(unittest.TestCase):
    def setUp(self):
        """测试前的准备工作"""
        self.debug_dir = "debug"
        self.test_html_file = os.path.join(self.debug_dir, "01_debug_original.html")

    def test_html_to_markdown_conversion(self):
        """测试 HTML 到 Markdown 的转换"""
        # 确保测试文件存在
        self.assertTrue(os.path.exists(self.test_html_file), 
                       f"测试文件不存在: {self.test_html_file}")

        # 读取测试 HTML 文件
        with open(self.test_html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 执行转换
        markdown_content, images = markdown_converter.convert(html_content)

        # 基本检查
        self.assertIsNotNone(markdown_content)
        self.assertIsInstance(markdown_content, str)
        self.assertGreater(len(markdown_content), 0)

        # 检查图片提取
        self.assertIsInstance(images, list)
        print(f"\n找到 {len(images)} 张图片:")
        for src, alt in images:
            print(f"- src: {src}")
            print(f"  alt: {alt}")

        # 打印转换后的 Markdown（用于手动检查）
        print("\n转换后的 Markdown 内容:")
        print("=" * 80)
        print(markdown_content)
        print("=" * 80)

if __name__ == '__main__':
    unittest.main() 
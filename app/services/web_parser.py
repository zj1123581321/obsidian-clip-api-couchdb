import requests
from bs4 import BeautifulSoup
from typing import Tuple, Optional
import re
import os
from ..services.notification import notifier
from ..config import config

class WebParser:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.debug_dir = "debug"

    def _save_debug_file(self, filename: str, content: str):
        """保存调试文件"""
        if config.debug:
            try:
                os.makedirs(self.debug_dir, exist_ok=True)
                filepath = os.path.join(self.debug_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                notifier.send_progress("调试信息", f"已保存调试文件: {filename}")
            except Exception as e:
                notifier.send_error(f"保存调试文件失败: {str(e)}")

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取网页标题"""
        # 1. 尝试从 meta 标签获取
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            return meta_title['content']

        # 2. 尝试从 title 标签获取
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.text.strip()

        # 3. 尝试从 h1 标签获取
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.text.strip()

        return ""

    def _clean_html(self, html: str) -> str:
        """清理 HTML 内容"""
        # 替换 data-src 为 src
        html = re.sub(r'data-src="([^"]*)"', r'src="\1"', html)
        return html

    def parse_url(self, url: str) -> Tuple[str, str, str]:
        """解析网页内容，返回标题、HTML 和清理后的 HTML"""
        try:
            notifier.send_progress("开始解析网页", f"正在获取网页内容: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            html = response.text
            cleaned_html = self._clean_html(html)
            
            # 保存原始 HTML
            self._save_debug_file("debug_original.html", html)
            self._save_debug_file("debug_cleaned.html", cleaned_html)
            
            soup = BeautifulSoup(cleaned_html, 'html.parser')
            title = self._extract_title(soup)
            
            if not title:
                title = "未命名文章"
                notifier.send_progress("警告", "未能提取到文章标题，使用默认标题")
            
            return title, html, cleaned_html
            
        except requests.RequestException as e:
            error_msg = f"获取网页内容失败: {str(e)}"
            notifier.send_error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"解析网页失败: {str(e)}"
            notifier.send_error(error_msg)
            raise Exception(error_msg)

# 创建全局解析器实例
web_parser = WebParser() 
"""
网页解析服务模块

负责获取和解析网页内容。
"""

import requests
from bs4 import BeautifulSoup
import re
import os
from ..services.notification import notifier
from ..config import config
from ..logger import logger

class WebParser:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.debug_dir = "debug"
        self.debug_seq = 1  # 调试文件序号

    def _save_debug_file(self, filename: str, content: str):
        """保存调试文件"""
        if config.debug:
            try:
                os.makedirs(self.debug_dir, exist_ok=True)
                # 添加序号前缀
                base, ext = os.path.splitext(filename)
                filename = f"{self.debug_seq:02d}_{base}{ext}"
                self.debug_seq += 1
                
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

    def _extract_meta_info(self, html: str) -> dict:
        """提取页面元数据信息"""
        import re
        
        soup = BeautifulSoup(html, 'html.parser')
        meta_info = {
            'author': '',
            'date': '',
            'description': ''
        }
        
        # 1. 提取作者信息
        # 尝试多种可能的 meta 标签
        author_meta = (
            soup.find('meta', {'name': 'author'}) or
            soup.find('meta', {'property': 'og:article:author'}) or
            soup.find('meta', {'property': 'article:author'}) or
            soup.find('meta', {'name': 'twitter:creator'})
        )
        if author_meta:
            meta_info['author'] = author_meta.get('content', '')
        
        # 2. 提取发布日期
        # 尝试多种可能的 meta 标签
        date_meta = (
            soup.find('meta', {'name': 'article:published_time'}) or
            soup.find('meta', {'property': 'article:published_time'}) or
            soup.find('meta', {'name': 'publishedDate'}) or
            soup.find('meta', {'name': 'date'})
        )
        if date_meta:
            meta_info['date'] = date_meta.get('content', '')
            
        # 如果没有找到日期，尝试在页面中查找日期格式的文本
        if not meta_info['date']:
            # 匹配常见的日期格式
            date_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
                r'\d{4}年\d{2}月\d{2}日'  # YYYY年MM月DD日
            ]
            for pattern in date_patterns:
                if match := re.search(pattern, html):
                    meta_info['date'] = match.group()
                    break
        
        # 3. 提取描述信息
        # 尝试多种可能的 meta 标签
        description_meta = (
            soup.find('meta', {'name': 'description'}) or
            soup.find('meta', {'property': 'og:description'}) or
            soup.find('meta', {'name': 'twitter:description'})
        )
        if description_meta:
            meta_info['description'] = description_meta.get('content', '')
        
        # 4. 微信公众号特殊处理
        if 'mp.weixin.qq.com' in html:
            # 微信公众号的发布时间通常在 JS 变量中
            publish_time_match = re.search(r'var publish_time = "([^"]+)"', html)
            if publish_time_match:
                meta_info['date'] = publish_time_match.group(1)
        
        return meta_info

    def parse_url(self, url: str) -> tuple:
        """解析网页内容，返回标题、HTML、清理后的HTML和元数据"""
        try:
            notifier.send_progress("开始解析网页", f"正在获取网页内容: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            html = response.text
            cleaned_html = self._clean_html(html)
            
            # 保存原始 HTML
            self._save_debug_file("web_original.html", html)
            self._save_debug_file("web_cleaned.html", cleaned_html)
            
            # 提取标题和元数据
            title = self._extract_title(BeautifulSoup(cleaned_html, 'html.parser'))
            meta_info = self._extract_meta_info(html)
            
            if not title:
                title = "未命名文章"
                notifier.send_progress("警告", "未能提取到文章标题，使用默认标题")
            
            return title, html, cleaned_html, meta_info
            
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
import trafilatura
from bs4 import BeautifulSoup
import re
import os
import time
from datetime import datetime
from typing import List, Tuple
from markdownify import markdownify as md
from ..services.notification import notifier
from ..config import config

class MarkdownConverter:
    def __init__(self):
        self.debug_dir = "debug"
        self.debug_seq = 1  # 调试文件序号

    def _log(self, message: str):
        """输出带时间戳的日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"[{timestamp}] {message}")

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
                self._log(f"已保存调试文件: {filename}")
            except Exception as e:
                self._log(f"保存调试文件失败: {str(e)}")

    def _extract_images(self, html: str) -> List[Tuple[str, str]]:
        """提取 HTML 中的所有图片链接"""
        start_time = time.time()
        self._log("开始提取图片链接")
        
        soup = BeautifulSoup(html, 'html.parser')
        images = []
        
        # 查找所有图片标签
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src:
                alt = img.get('alt', '')
                images.append((src, alt))
                # 在原始 HTML 中标记已处理的图片
                img['data-processed'] = 'true'
        
        # 保存图片链接列表
        if images:
            self._save_debug_file("debug_images.txt", 
                                "\n".join([f"{src}\t{alt}" for src, alt in images]))
        
        elapsed = time.time() - start_time
        self._log(f"图片链接提取完成，找到 {len(images)} 张图片，耗时: {elapsed:.2f}秒")
        return images

    def _clean_html(self, html: str) -> str:
        """清理 HTML，移除不需要的标签，并保持正确的段落格式"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除不需要的标签
        for tag in soup(['script', 'style', 'meta', 'link', 'noscript', 'iframe']):
            tag.decompose()
            
        # 移除空的 span 标签
        for span in soup.find_all('span'):
            if not span.get_text(strip=True):
                span.decompose()
                
        # 处理链接
        for a in soup.find_all('a'):
            href = a.get('href', '')
            text = a.get_text(strip=True)
            
            if not href or 'javascript:' in href:
                # 如果没有链接或是 javascript 链接，只保留文本
                if text:
                    a.replace_with(text)
                else:
                    a.decompose()
            else:
                # 保留有效的链接，不修改链接文本
                continue

        # 处理 section 标签
        for section in soup.find_all('section'):
            # 检查 section 是否包含链接
            links = section.find_all('a')
            if links:
                # 如果包含链接，保持原有结构，在 section 后添加两个换行符
                section.append(soup.new_string('\n\n'))
            else:
                # 如果不包含链接，提取文本内容
                span = section.find('span')
                if span:
                    text = span.get_text()
                    new_text = soup.new_string(text + '\n\n')
                    section.clear()
                    section.append(new_text)
                elif section.get_text(strip=True):
                    text = section.get_text()
                    new_text = soup.new_string(text + '\n\n')
                    section.clear()
                    section.append(new_text)

        # 确保标题前后有换行
        for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if h.previous_sibling:
                h.insert_before(soup.new_string('\n\n'))
            if h.next_sibling:
                h.append(soup.new_string('\n\n'))
        
        return str(soup)

    def _clean_wechat_content(self, html: str) -> str:
        """清理微信公众号文章的额外内容"""
        # 查找截断词的位置
        cut_point = html.find("预览时标签不可点")
        if cut_point == -1:
            return html
            
        # 截取有效内容
        return html[:cut_point].strip()

    def convert(self, html: str) -> Tuple[str, List[Tuple[str, str]]]:
        """将 HTML 转换为 Markdown，并提取图片信息"""
        try:
            start_time = time.time()
            self._log("开始转换 HTML 到 Markdown")
            
            # 保存原始 HTML
            self._save_debug_file("debug_original.html", html)
            
            # 清理微信公众号文章的额外内容
            html = self._clean_wechat_content(html)
            
            # 提取图片信息
            images = self._extract_images(html)
            
            # 清理 HTML
            html = self._clean_html(html)
            
            # 保存处理后的 HTML
            self._save_debug_file("debug_processed.html", html)
            
            # 使用 markdownify 转换为 Markdown
            markdown = md(html,
                heading_style="ATX",  # 使用 # 样式的标题
                bullets="-",  # 使用 - 作为无序列表标记
                autolinks=True,  # 自动转换链接
                wrap=False,  # 不自动换行
                default_title=True,  # 使用默认标题
                escape_underscores=True,  # 转义下划线
                newline_style="\n",  # 使用 \n 作为换行符
                strip=['script', 'style', 'meta', 'link', 'noscript', 'iframe'],  # 要移除的标签
                options={
                    'emphasis_mark': '*',  # 使用 * 作为强调标记
                    'code_mark': '`',  # 使用 ` 作为代码标记
                    'hr_mark': '---',  # 使用 --- 作为分隔线
                    'br_mark': '  \n',  # 使用两个空格加换行作为软换行
                    'strong_mark': '**',  # 使用 ** 作为加粗标记
                    'link_brackets': True,  # 使用 [] 和 () 包裹链接
                    'convert_links': True,  # 转换链接
                    'keep_links': True,  # 保持链接
                }
            )
            
            # 处理连续的空行，最多保留两个换行
            markdown = re.sub(r'\n{3,}', '\n\n', markdown)
            
            # 处理链接之间的换行，确保每个链接后有两个换行符
            markdown = re.sub(r'(\[.*?\]\(.*?\))\n', r'\1\n\n', markdown)
            
            # 保存转换后的 Markdown
            self._save_debug_file("debug_result.md", markdown)
            
            elapsed = time.time() - start_time
            self._log(f"Markdown 转换完成，耗时: {elapsed:.2f}秒")
            
            return markdown, images
            
        except Exception as e:
            error_msg = f"转换 Markdown 失败: {str(e)}"
            self._log(error_msg)
            raise Exception(error_msg)

# 创建全局转换器实例
markdown_converter = MarkdownConverter() 
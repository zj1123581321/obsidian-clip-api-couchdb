"""
Markdown 转换服务模块

负责将 HTML 转换为 Markdown 格式。
"""

from bs4 import BeautifulSoup
import re
import time
from typing import List, Tuple
from markdownify import markdownify as md
from ..services.notification import notifier
from ..config import config
from ..logger import logger
from ..utils.debug_manager import debug_manager


class MarkdownConverter:
    """Markdown 转换服务，负责将 HTML 转换为 Markdown"""

    def __init__(self):
        """初始化 Markdown 转换器"""
        pass

    def _extract_images(self, html: str) -> List[Tuple[str, str]]:
        """提取 HTML 中的所有图片链接

        同时支持 src 和 data-src 属性（微信公众号使用 data-src 懒加载）。
        优先使用 src 属性，如果没有则使用 data-src。

        Args:
            html: HTML 内容

        Returns:
            List[Tuple[str, str]]: 图片链接和 alt 文本的列表
        """
        start_time = time.time()
        logger.debug("开始提取图片链接")

        soup = BeautifulSoup(html, 'html.parser')
        images = []

        # 查找所有图片标签
        for img in soup.find_all('img'):
            # 优先使用 src，如果没有则使用 data-src（微信懒加载）
            src = img.get('src', '') or img.get('data-src', '')
            if src:
                alt = img.get('alt', '')
                images.append((src, alt))
                # 在原始 HTML 中标记已处理的图片
                img['data-processed'] = 'true'
        
        # 保存图片链接列表（调试用）
        if images:
            debug_manager.save_file(
                "images.txt",
                "\n".join([f"{src}\t{alt}" for src, alt in images]),
                prefix="md"
            )
        
        elapsed = time.time() - start_time
        logger.debug(f"图片链接提取完成，找到 {len(images)} 张图片，耗时: {elapsed:.2f}秒")
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
            # 检查 section 是否包含链接或标题
            links = section.find_all('a')
            headings = section.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            images = section.find_all('img')

            if links or headings or images:
                # 如果包含链接、标题或图片，保持原有结构
                section.append(soup.new_string('\n\n'))
            else:
                # 如果不包含重要元素，提取文本内容
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

    def _extract_wechat_js_content(self, html: str) -> str:
        """从微信公众号 JavaScript 变量中提取文章内容

        微信公众号文章内容存储在 JS 变量 content_noencode 中，
        格式为: content_noencode: JsDecode('...')

        Args:
            html: 原始 HTML

        Returns:
            str: 提取的文章内容（HTML 格式），如果提取失败返回空字符串
        """
        # 匹配 content_noencode: JsDecode('...')
        pattern = r"content_noencode:\s*JsDecode\('([^']+)'\)"
        match = re.search(pattern, html)

        if not match:
            return ""

        content = match.group(1)

        # 解码转义字符
        content = content.replace('\\x0a', '\n')
        content = content.replace('\\x3c', '<')
        content = content.replace('\\x3e', '>')
        content = content.replace('\\x22', '"')
        content = content.replace('\\x26amp;', '&')
        content = content.replace('\\x27', "'")
        content = content.replace('\\/', '/')
        content = content.replace('\\\\', '\\')

        logger.debug(f"从微信 JS 变量中提取到文章内容，长度: {len(content)}")
        return content

    def _extract_wechat_images(self, html: str) -> List[Tuple[str, str]]:
        """从微信 picture_page_info_list 提取正文图片

        微信公众号的正文图片存储在 JS 变量 picture_page_info_list 中，
        而不是直接在 <img> 标签里。需要解析这个变量来获取图片 URL。

        注意：每个图片对象包含多个 cdn_url（主图、水印图、分享封面等），
        只需要提取每个对象开头的主图 cdn_url。

        Args:
            html: 原始 HTML

        Returns:
            List[Tuple[str, str]]: 图片 URL 和 alt 文本的列表
        """
        # 匹配 picture_page_info_list 变量
        pattern = r"picture_page_info_list\s*=\s*(\[[\s\S]*?\])\s*\.slice"
        match = re.search(pattern, html)
        if not match:
            return []

        raw_list = match.group(1)

        # 按图片对象分割（每个对象以 { 开头，包含 width/height/cdn_url）
        # 只提取每个对象的第一个 cdn_url（主图），忽略 watermark_info 和 share_cover 中的
        object_pattern = r"\{\s*width:[^}]*?cdn_url:\s*'([^']+)'"
        main_urls = re.findall(object_pattern, raw_list)

        images = []
        seen = set()
        for url in main_urls:
            # 解码转义字符
            url = url.replace('\\x26amp;', '&')
            url = url.replace('\\x26', '&')
            url = url.replace('\\x22', '"')

            # 跳过已处理的 URL
            if url in seen:
                continue
            seen.add(url)
            images.append((url, ''))

        logger.debug(f"从微信 picture_page_info_list 提取到 {len(images)} 张主图")
        return images

    def _clean_wechat_content(self, html: str) -> str:
        """清理微信公众号文章的额外内容

        采用降级策略：
        1. 优先使用截断方式（保留完整 HTML 结构，图片和文本不会丢失）
        2. 如果找不到截断点，再尝试从 JS 变量提取（适用于新类型微信链接）

        Args:
            html: 原始 HTML

        Returns:
            str: 清理后的 HTML 内容
        """
        # 方式1：优先使用截断逻辑（旧方式，兼容性好）
        cut_point = html.find("预览时标签不可点")
        if cut_point != -1:
            logger.info("[MarkdownConverter] 解析方式: 截断提取（保留完整HTML结构）")
            return html[:cut_point].strip()

        # 方式2：降级到 JS 变量提取（适用于新类型链接）
        js_content = self._extract_wechat_js_content(html)
        if js_content:
            logger.info("[MarkdownConverter] 解析方式: JS变量提取（降级模式）")
            # 将提取的内容转换为 HTML 结构
            paragraphs = js_content.split('\n\n')
            html_paragraphs = []
            for p in paragraphs:
                p = p.strip()
                if p:
                    # 保留已有的 HTML 标签（如链接、图片）
                    if '<a ' in p or '<img ' in p:
                        html_paragraphs.append(f"<p>{p}</p>")
                    else:
                        # 处理单个换行
                        p = p.replace('\n', '<br/>')
                        html_paragraphs.append(f"<p>{p}</p>")
            result = '\n'.join(html_paragraphs)
            # 将 data-src 替换为 src，确保 markdownify 能正确转换图片
            result = re.sub(r'data-src="([^"]*)"', r'src="\1"', result)
            return result

        # 方式3：都不适用，返回原始 HTML
        logger.info("[MarkdownConverter] 解析方式: 原始HTML（非微信文章或格式未识别）")
        return html

    def convert(self, html: str) -> Tuple[str, List[Tuple[str, str]]]:
        """将 HTML 转换为 Markdown，并提取图片信息"""
        try:
            start_time = time.time()
            logger.info("[MarkdownConverter] 开始转换 HTML 到 Markdown")

            # 保存原始 HTML（调试用）
            debug_manager.save_file("original.html", html, prefix="md")

            # 先从原始 HTML 提取微信正文图片（在清理之前）
            # 微信公众号的正文图片存储在 JS 变量中，清理后会丢失
            wechat_images = self._extract_wechat_images(html)

            # 清理微信公众号文章的额外内容
            html = self._clean_wechat_content(html)

            # 从清理后的 HTML 提取 img 标签中的图片
            tag_images = self._extract_images(html)

            # 合并图片列表，微信正文图片优先，去重
            seen_urls = set()
            images = []
            for img_url, alt in wechat_images + tag_images:
                if img_url not in seen_urls:
                    seen_urls.add(img_url)
                    images.append((img_url, alt))

            if wechat_images:
                logger.info(f"[MarkdownConverter] 图片来源: 微信JS={len(wechat_images)}, HTML标签={len(tag_images)}, 合并后={len(images)}")
            
            # 清理 HTML
            html = self._clean_html(html)
            
            # 保存处理后的 HTML（调试用）
            debug_manager.save_file("processed.html", html, prefix="md")
            
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

            # 如果有从微信 JS 变量提取的图片，但 Markdown 中没有图片标记，
            # 需要将图片插入到正文中（因为 JS 变量提取模式下正文不包含图片）
            if wechat_images and '![' not in markdown:
                logger.debug(f"[MarkdownConverter] 正文无图片，插入 {len(wechat_images)} 张微信图片")
                # 在文章开头插入图片
                image_section = '\n\n'.join([f'![图片{i+1}]({url})' for i, (url, _) in enumerate(wechat_images)])
                markdown = image_section + '\n\n' + markdown

            # 保存转换后的 Markdown（调试用）
            debug_manager.save_file("result.md", markdown, prefix="md")
            
            elapsed = time.time() - start_time
            logger.info(f"[MarkdownConverter] 转换完成: images={len(images)}, time={elapsed:.2f}s")
            
            return markdown, images
            
        except Exception as e:
            error_msg = f"转换 Markdown 失败: {str(e)}"
            logger.error(f"[MarkdownConverter] {error_msg}")
            raise Exception(error_msg)

# 创建全局转换器实例
markdown_converter = MarkdownConverter() 
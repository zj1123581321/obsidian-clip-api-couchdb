"""
外部 URL Parse API 服务模块

该模块负责调用外部 URL Parse API 获取网页内容，
作为内置 web_parser + markdown_converter 的替代方案。
"""

import aiohttp
from typing import Tuple, List, Dict, Optional
from ..config import config
from ..logger import logger


class UrlParseService:
    """外部 URL Parse API 客户端"""

    def __init__(self):
        self._reload_config()

    def _reload_config(self):
        """重新加载配置"""
        self.api_url = config.get('content_fetcher.external.url', '')
        self.api_key = config.get('content_fetcher.external.api_key', '')
        self.timeout = config.get('content_fetcher.external.timeout', 60)
        self.use_cache = config.get('content_fetcher.external.use_cache', True)
        self.force_fetcher = config.get('content_fetcher.external.force_fetcher', '')

    async def fetch_content(self, url: str) -> Tuple[str, str, List[Tuple[str, str]], dict]:
        """调用外部 URL Parse API 获取网页内容

        Args:
            url: 目标网页 URL

        Returns:
            Tuple: (title, markdown, images, meta_info)
                - title: 文章标题
                - markdown: Markdown 格式正文
                - images: 图片列表 [(url, alt), ...]
                - meta_info: 元数据 dict {author, date, description}

        Raises:
            Exception: API 调用失败时抛出异常
        """
        self._reload_config()

        if not self.api_url:
            raise Exception("外部 URL Parse API 地址未配置，请检查 content_fetcher.external.url")

        logger.info(f"[UrlParse] 调用外部 API 解析: {url}")

        # 构建请求
        payload = {"url": url}
        options = {}
        if not self.use_cache:
            options["use_cache"] = False
        if self.force_fetcher:
            options["force_fetcher"] = self.force_fetcher
        if self.timeout != 30:
            options["timeout"] = self.timeout
        if options:
            payload["options"] = options

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = aiohttp.ClientTimeout(total=self.timeout + 10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.api_url, json=payload, headers=headers) as response:
                if response.status == 429:
                    retry_after = response.headers.get("Retry-After", "5")
                    raise Exception(f"外部 API 频率限制，请 {retry_after} 秒后重试")

                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"外部 API 返回错误状态码 {response.status}: {error_text[:200]}")

                data = await response.json()

        if not data.get("success"):
            error = data.get("error", "未知错误")
            raise Exception(f"外部 API 提取失败: {error}")

        return self._parse_response(data)

    def _parse_response(self, data: dict) -> Tuple[str, str, List[Tuple[str, str]], dict]:
        """解析外部 API 响应，映射为内部格式

        Args:
            data: API 响应 JSON

        Returns:
            Tuple: (title, markdown, images, meta_info)
        """
        title = data.get("title") or "未命名文章"
        markdown = data.get("content_markdown") or ""

        # 映射图片列表: [{url, alt, type}] -> [(url, alt)]
        images = []
        media = data.get("media")
        if media and media.get("images"):
            for img in media["images"]:
                img_url = img.get("url", "")
                img_alt = img.get("alt", "")
                if img_url:
                    images.append((img_url, img_alt or ""))

        # 映射元数据
        metadata = data.get("metadata") or {}
        meta_info = {
            "author": metadata.get("author", ""),
            "date": metadata.get("publish_date", ""),
            "description": metadata.get("description", ""),
        }

        fetcher_used = data.get("fetcher_used", "unknown")
        elapsed_ms = data.get("elapsed_ms", 0)
        cached = data.get("cached", False)
        logger.info(
            f"[UrlParse] 解析完成: title='{title[:30]}...', "
            f"images={len(images)}, fetcher={fetcher_used}, "
            f"elapsed={elapsed_ms}ms, cached={cached}"
        )

        return title, markdown, images, meta_info


# 创建全局服务实例
url_parse_service = UrlParseService()

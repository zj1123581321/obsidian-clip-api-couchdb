from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional
import asyncio
from datetime import datetime
from ..services.web_parser import web_parser
from ..services.markdown_converter import markdown_converter
from ..services.image_uploader import image_uploader
from ..services.couchdb_service import couchdb_service
from ..services.notification import notifier
from ..config import config

router = APIRouter()

class ClipRequest(BaseModel):
    url: HttpUrl

class ClipResponse(BaseModel):
    title: str
    doc_id: Optional[str] = None
    error: Optional[str] = None

def generate_yaml_front_matter(url: str, title: str, meta_info: dict) -> str:
    """生成 YAML front matter
    
    Args:
        url: 原文链接
        title: 文章标题
        meta_info: 元数据信息，包含 author、date、description
        
    Returns:
        str: YAML front matter 文本，包含以下属性（按顺序）：
        - url: 原文链接
        - title: 文章标题
        - description: 文章描述
        - author: 文章作者
        - published: 文章发布日期
        - created: 剪藏时间（Obsidian 格式）
    """
    # 使用 Obsidian 格式的时间戳：YYYY-MM-DD HH:mm
    created = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    return f"""---
url: {url}
title: {title}
description: {meta_info.get('description', '')}
author: {meta_info.get('author', '')}
published: {meta_info.get('date', '')}
created: {created}
---

"""

@router.post("/clip", response_model=ClipResponse)
async def clip_article(request: ClipRequest):
    """剪藏文章 API"""
    try:
        # 发送剪藏开始通知
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        picgo_enabled = config.get('picgo', {}).get('enabled', False)
        notifier.send_message(
            f"📥 开始剪藏\n"
            f"时间：{current_time}\n"
            f"链接：{request.url}\n"
            f"图床：{'已开启' if picgo_enabled else '未开启'}"
        )
        
        # 1. 解析网页
        title, html, cleaned_html, meta_info = web_parser.parse_url(str(request.url))
        
        # 2. 转换为 Markdown
        markdown, images = markdown_converter.convert(cleaned_html)
        
        # 3. 根据配置决定是否处理图片
        if picgo_enabled and images:
            notifier.send_progress("图片处理", "开始上传图片到图床")
            # 上传图片并替换 URL
            url_mapping = await image_uploader.upload_images(images)
            markdown = image_uploader.replace_image_urls(markdown, url_mapping)
        else:
            if not picgo_enabled:
                notifier.send_progress("图片处理", "图床功能未启用，保持原始图片链接")
            elif not images:
                notifier.send_progress("图片处理", "文章中未发现图片")
        
        # 添加 YAML front matter 和 Obsidian 标签
        full_content = generate_yaml_front_matter(str(request.url), title, meta_info) + markdown
        
        # 4. 保存到 CouchDB
        doc_id = couchdb_service.save_document(title, full_content, str(request.url))
        
        # 5. 发送成功通知（合并中间和最后的通知）
        doc_path = couchdb_service.get_document_path(doc_id)
        notifier.send_message(
            f"✅ 剪藏成功\n"
            f"标题：{title}\n"
            f"链接：{request.url}\n"
            f"路径：{doc_path}"
        )
        
        return ClipResponse(
            title=title,
            doc_id=doc_id
        )
        
    except Exception as e:
        error_msg = str(e)
        notifier.send_error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg) 
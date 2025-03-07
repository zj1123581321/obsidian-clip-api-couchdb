from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional
import asyncio
from ..services.web_parser import web_parser
from ..services.markdown_converter import markdown_converter
from ..services.image_uploader import image_uploader
from ..services.couchdb_service import couchdb_service
from ..services.notification import notifier

router = APIRouter()

class ClipRequest(BaseModel):
    url: HttpUrl

class ClipResponse(BaseModel):
    title: str
    doc_id: Optional[str] = None
    error: Optional[str] = None

@router.post("/clip", response_model=ClipResponse)
async def clip_article(request: ClipRequest):
    """剪藏文章 API"""
    try:
        # 1. 解析网页
        title, html, cleaned_html = web_parser.parse_url(str(request.url))
        
        # 2. 转换为 Markdown
        markdown, images = markdown_converter.convert(cleaned_html)
        
        # 3. 上传图片
        url_mapping = await image_uploader.upload_images(images)
        markdown = image_uploader.replace_image_urls(markdown, url_mapping)
        
        # 4. 保存到 CouchDB
        doc_id = couchdb_service.save_document(title, markdown, str(request.url))
        
        # 5. 发送成功通知
        notifier.send_success(title, str(request.url))
        
        return ClipResponse(
            title=title,
            doc_id=doc_id
        )
        
    except Exception as e:
        error_msg = str(e)
        notifier.send_error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg) 
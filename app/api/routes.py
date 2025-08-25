from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, HttpUrl
from typing import Optional
import asyncio
from datetime import datetime
from ..services.web_parser import web_parser
from ..services.markdown_converter import markdown_converter
from ..services.image_uploader import image_uploader
from ..services.couchdb_service import couchdb_service
from ..services.obsidian_rest_api import obsidian_rest_api
from ..services.notification import notifier
from ..config import config

router = APIRouter()

class ClipRequest(BaseModel):
    url: HttpUrl

class ClipResponse(BaseModel):
    title: str
    doc_id: Optional[str] = None
    error: Optional[str] = None

async def verify_api_key(x_api_key: str = Header(None)):
    """验证 API 密钥
    
    Args:
        x_api_key: 请求头中的 API 密钥
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        HTTPException: 验证失败时抛出异常
    """
    # 检查是否启用 API 鉴权
    if not config.get('api', {}).get('enabled', False):
        return True
        
    # 获取配置的 API 密钥
    api_key = config.get('api', {}).get('key')
    if not api_key:
        raise HTTPException(status_code=500, detail="API 密钥未配置")
        
    # 验证 API 密钥
    if not x_api_key or x_api_key != api_key:
        raise HTTPException(
            status_code=401,
            detail="无效的 API 密钥"
        )
    return True

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
async def clip_article(
    request: ClipRequest,
    verified: bool = Depends(verify_api_key)
):
    """剪藏文章 API
    
    Args:
        request: 剪藏请求
        verified: API 密钥验证结果
        
    Returns:
        ClipResponse: 剪藏结果
    """
    try:
        # 发送剪藏开始通知
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        picgo_enabled = config.get('picgo', {}).get('enabled', False)
        storage_method = config.storage_method
        notifier.send_message(
            f"📥 开始剪藏\n"
            f"时间：{current_time}\n"
            f"链接：{request.url}\n"
            f"存储：{storage_method.upper()}\n"
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
        
        # 4. 根据配置选择存储方式
        storage_method = config.storage_method
        
        if storage_method == 'rest_api':
            # 使用 Obsidian REST API
            if not config.obsidian_api_key:
                raise Exception("Obsidian REST API 密钥未配置，请检查 obsidian_api.api_key 配置项")
            
            # 添加向后兼容性提醒
            if config.get('couchdb.url'):
                notifier.send_progress("提醒", "检测到 CouchDB 配置，建议迁移到 REST API 方式")
            
            file_path = await obsidian_rest_api.save_document(title, full_content, str(request.url))
            
            notifier.send_message(
                f"✅ 剪藏成功\n"
                f"标题：{title}\n"
                f"链接：{request.url}\n"
                f"路径：{file_path}"
            )
            
            return ClipResponse(
                title=title,
                doc_id=file_path  # REST API 返回文件路径作为 doc_id
            )
            
        else:
            # 使用 CouchDB（向后兼容）
            if storage_method == 'couchdb':
                notifier.send_progress("提醒", "⚠️ CouchDB 存储方式将在未来版本中废弃，建议切换到 REST API 方式")
            
            doc_id = couchdb_service.save_document(title, full_content, str(request.url))
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


@router.get("/health")
async def health_check():
    """健康检查接口，检查各个服务的状态"""
    storage_method = config.storage_method
    result = {
        "storage_method": storage_method,
        "status": "ok",
        "services": {}
    }
    
    try:
        if storage_method == 'rest_api':
            # 检查 Obsidian REST API
            if config.obsidian_api_key:
                connection_info = await obsidian_rest_api.test_connection()
                result["services"]["obsidian_api"] = connection_info
            else:
                result["services"]["obsidian_api"] = {
                    "status": "not_configured",
                    "error": "API Key 未配置"
                }
        
        # 检查图床服务（如果启用）
        picgo_enabled = config.get('picgo', {}).get('enabled', False)
        result["services"]["picgo"] = {
            "enabled": picgo_enabled,
            "status": "configured" if picgo_enabled else "disabled"
        }
        
        # 检查企业微信（如果配置）
        wechat_configured = bool(config.work_wechat_corp_id)
        result["services"]["work_wechat"] = {
            "configured": wechat_configured,
            "status": "configured" if wechat_configured else "not_configured"
        }
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result 
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime
from ..services.web_parser import web_parser
from ..services.markdown_converter import markdown_converter
from ..services.image_uploader import image_uploader
from ..services.couchdb_service import couchdb_service
from ..services.obsidian_rest_api import obsidian_rest_api
from ..services.notification import notifier
from ..services.llm_service import llm_service, LLMResult
from ..services.url_parse_service import url_parse_service
from ..config import config
from ..logger import logger
from ..utils.debug_manager import debug_manager

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

def _format_yaml_list(items: List[str], indent: int = 2) -> str:
    """格式化列表为 YAML 格式

    Args:
        items: 字符串列表
        indent: 缩进空格数

    Returns:
        str: YAML 格式的列表字符串
    """
    if not items:
        return "[]"

    indent_str = " " * indent
    escaped_items = []
    for item in items:
        # 转义双引号和反斜杠，确保 YAML 解析正确
        escaped = item.replace('\\', '\\\\').replace('"', '\\"')
        escaped_items.append(f'\n{indent_str}- "{escaped}"')
    return "".join(escaped_items)


def _escape_yaml_string(value: str) -> str:
    """转义 YAML 字符串中的特殊字符

    Args:
        value: 原始字符串

    Returns:
        str: 转义后的字符串
    """
    if not value:
        return ""
    # 如果包含特殊字符，用引号包裹并转义
    special_chars = [':', '#', '"', "'", '\n', '[', ']', '{', '}', '\\']
    if any(c in value for c in special_chars):
        # 先转义反斜杠，再转义双引号
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return value


def generate_yaml_front_matter(
    url: str,
    title: str,
    meta_info: dict,
    llm_result: Optional[LLMResult] = None
) -> str:
    """生成 YAML front matter

    Args:
        url: 原文链接
        title: 文章标题
        meta_info: 元数据信息，包含 author、date、description
        llm_result: LLM 处理结果（可选）

    Returns:
        str: YAML front matter 文本
    """
    # 使用 Obsidian 格式的时间戳：YYYY-MM-DD HH:mm
    created = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 基础字段
    yaml_content = f"""---
url: {_escape_yaml_string(url)}
title: {_escape_yaml_string(title)}
description: {_escape_yaml_string(meta_info.get('description', ''))}
author: {_escape_yaml_string(meta_info.get('author', ''))}
published: {_escape_yaml_string(meta_info.get('date', ''))}
created: {created}"""

    # 如果有 LLM 结果，添加 LLM 生成的字段
    if llm_result and llm_result.success:
        llm_data = llm_result.to_yaml_dict()

        yaml_content += f"""
category: {_escape_yaml_string(llm_data.get('category', ''))}
new_title: {_escape_yaml_string(llm_data.get('new_title', ''))}
score: {llm_data.get('score', 0)}
score_plus: {_format_yaml_list(llm_data.get('score_plus', []))}
score_minus: {_format_yaml_list(llm_data.get('score_minus', []))}
entities_company_worldwide: {_format_yaml_list(llm_data.get('entities_company_worldwide', []))}
entities_company_domestic: {_format_yaml_list(llm_data.get('entities_company_domestic', []))}
entities_vip_worldwide: {_format_yaml_list(llm_data.get('entities_vip_worldwide', []))}
entities_vip_domestic: {_format_yaml_list(llm_data.get('entities_vip_domestic', []))}
entities_industry_upper: {_format_yaml_list(llm_data.get('entities_industry_upper', []))}
entities_industry_mid: {_format_yaml_list(llm_data.get('entities_industry_mid', []))}
entities_industry_lower: {_format_yaml_list(llm_data.get('entities_industry_lower', []))}
paragraphs: {_format_yaml_list(llm_data.get('paragraphs', []))}
hidden_info: {_format_yaml_list(llm_data.get('hidden_info', []))}
golden_sentences: {_format_yaml_list(llm_data.get('golden_sentences', []))}"""

    yaml_content += "\n---\n\n"
    return yaml_content

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
        # 开始新的调试会话（按时间戳创建子文件夹）
        debug_manager.start_session()

        # 发送剪藏开始通知
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        picgo_enabled = config.get('picgo', {}).get('enabled', False)
        storage_method = config.storage_method
        notifier.send_message(
            f"⏰ {current_time}\n"
            f"📥 开始剪藏\n"
            f"链接：{request.url}\n"
            f"解析：{config.content_fetcher_method}\n"
            f"存储：{storage_method.upper()}\n"
            f"图床：{'已开启' if picgo_enabled else '未开启'}"
        )
        
        # 1. 获取网页内容（内置解析 或 外部 URL Parse API）
        fetcher_method = config.content_fetcher_method
        if fetcher_method == 'external':
            try:
                title, markdown, images, meta_info = await url_parse_service.fetch_content(str(request.url))
                notifier.send_progress("内容获取", f"[OK] 外部 API 解析完成: {title[:30]}...")
            except Exception as e:
                if config.content_fetcher_fallback:
                    logger.warning(f"[UrlParse] 外部 API 失败，回退到内置解析: {e}")
                    notifier.send_progress("内容获取", f"[WARN] 外部 API 失败，回退到内置解析: {str(e)[:80]}")
                    title, html, cleaned_html, meta_info = web_parser.parse_url(str(request.url))
                    markdown, images = markdown_converter.convert(cleaned_html)
                else:
                    raise
        else:
            title, html, cleaned_html, meta_info = web_parser.parse_url(str(request.url))
            markdown, images = markdown_converter.convert(cleaned_html)
        
        # 3. 并行处理：图片上传 + LLM 处理
        # 创建并行任务
        tasks = []
        task_names = []

        # 图片上传任务
        if picgo_enabled and images:
            notifier.send_progress("图片处理", "开始上传图片到图床")
            tasks.append(image_uploader.upload_images(images))
            task_names.append("image_upload")
        else:
            if not picgo_enabled:
                notifier.send_progress("图片处理", "图床功能未启用，保持原始图片链接")
            elif not images:
                notifier.send_progress("图片处理", "文章中未发现图片")

        # LLM 处理任务
        llm_enabled = llm_service.is_enabled()
        if llm_enabled:
            notifier.send_progress("LLM 处理", "开始调用外部 LLM API")
            tasks.append(llm_service.process(title, markdown, url=str(request.url)))
            task_names.append("llm_process")
        else:
            notifier.send_progress("LLM 处理", "功能未启用")

        # 并行执行所有任务
        url_mapping = {}
        llm_result = None

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            for i, result in enumerate(results):
                task_name = task_names[i]

                if isinstance(result, Exception):
                    notifier.send_progress(task_name, f"[ERROR] 执行失败: {str(result)}")
                    continue

                if task_name == "image_upload":
                    url_mapping = result
                    notifier.send_progress("图片处理", f"[OK] 上传完成，处理 {len(url_mapping)} 张图片")
                elif task_name == "llm_process":
                    llm_result = result
                    if llm_result and llm_result.success:
                        notifier.send_progress(
                            "LLM 处理",
                            f"[OK] 处理成功，分类: {llm_result.category}，耗时: {llm_result.processing_time:.1f}秒"
                        )
                    else:
                        notifier.send_progress("LLM 处理", "[WARN] 处理失败，继续保存文章")

        # 替换图片 URL（如果有上传）
        if url_mapping:
            markdown = image_uploader.replace_image_urls(markdown, url_mapping)

        # 添加 YAML front matter 和 Obsidian 标签
        full_content = generate_yaml_front_matter(str(request.url), title, meta_info, llm_result) + markdown

        # 5. 根据配置选择存储方式
        storage_method = config.storage_method
        
        if storage_method == 'rest_api':
            # 使用 Obsidian REST API
            if not config.obsidian_api_key:
                raise Exception("Obsidian REST API 密钥未配置，请检查 obsidian_api.api_key 配置项")
            
            # 添加向后兼容性提醒
            if config.get('couchdb.url'):
                notifier.send_progress("提醒", "检测到 CouchDB 配置，建议迁移到 REST API 方式")
            
            file_path = await obsidian_rest_api.save_document(title, full_content, str(request.url))

            notifier.send_clip_success(
                title=title,
                url=str(request.url),
                doc_path=file_path,
                llm_result=llm_result
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

            notifier.send_clip_success(
                title=title,
                url=str(request.url),
                doc_path=doc_path,
                llm_result=llm_result
            )
            
            return ClipResponse(
                title=title,
                doc_id=doc_id
            )
        
    except Exception as e:
        error_msg = str(e)
        notifier.send_error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        # 结束调试会话
        debug_manager.end_session()


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
        
        # 检查企业微信通知
        wechat_enabled = config.work_wechat_enabled and bool(config.work_wechat_webhook_url)
        result["services"]["work_wechat"] = {
            "enabled": wechat_enabled,
            "status": "enabled" if wechat_enabled else "disabled"
        }

        # 检查 LLM 服务
        llm_enabled = llm_service.is_enabled()
        result["services"]["llm"] = {
            "enabled": llm_enabled,
            "status": "configured" if llm_enabled else "disabled",
            "url": config.llm_url if llm_enabled else None
        }

        # 检查内容获取方式
        fetcher_method = config.content_fetcher_method
        if fetcher_method == 'external':
            result["services"]["content_fetcher"] = {
                "method": "external",
                "url": config.content_fetcher_external_url,
                "status": "configured" if config.content_fetcher_external_url else "not_configured",
                "fallback": config.content_fetcher_fallback
            }
        else:
            result["services"]["content_fetcher"] = {
                "method": "builtin",
                "status": "active"
            }

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result 
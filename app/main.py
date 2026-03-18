"""
Obsidian Clip API 主入口模块

提供网页剪藏到 Obsidian 的 API 服务。
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router
from .config import config
from .logger import logger, setup_logger
from .services.notification import notifier

# 根据配置初始化日志系统
setup_logger(
    level=config.log_level,
    colorize=config.log_colorize,
    rotation=config.log_rotation,
    retention=config.log_retention,
    compression=config.log_compression,
)


_TZ_BEIJING = timezone(timedelta(hours=8))


def _now_beijing() -> str:
    """返回北京时间格式化字符串"""
    return datetime.now(_TZ_BEIJING).strftime("%Y-%m-%d %H:%M:%S")


def _build_config_status() -> str:
    """构建当前配置状态摘要"""
    picgo_enabled = config.get('picgo', {}).get('enabled', False)
    llm_enabled = config.llm_enabled
    fetcher_method = config.content_fetcher_method
    fallback = config.content_fetcher_fallback

    fetcher_display = fetcher_method
    if fetcher_method == 'external':
        fetcher_display += f" (fallback: {'✅' if fallback else '❌'})"

    lines = [
        f"🗄️ 存储：{config.storage_method.upper()}",
        f"🔍 解析：{fetcher_display}",
        f"🖼️ 图床：{'✅ 已开启' if picgo_enabled else '❌ 未开启'}",
        f"🤖 LLM：{'✅ 已开启' if llm_enabled else '❌ 未开启'}",
        f"📝 日志：{config.log_level}",
    ]
    return "\n".join(lines)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # --- 启动 ---
    logger.info("[API] Obsidian Clip API 服务启动")
    logger.info(f"[API] 日志级别: {config.log_level}")
    logger.info(f"[API] 存储方式: {config.storage_method}")
    logger.info(f"[API] 内容获取: {config.content_fetcher_method}")
    logger.info(f"[API] 图床功能: {'启用' if config.get('picgo.enabled', False) else '禁用'}")
    logger.info(f"[API] LLM 处理: {'启用' if config.llm_enabled else '禁用'}")

    status = _build_config_status()
    notifier.send_message(f"⏰ {_now_beijing()}\n🟢 Obsidian Clip API 已启动\n\n{status}")

    yield

    # --- 关闭 ---
    logger.info("[API] Obsidian Clip API 服务关闭")
    notifier.send_message(f"⏰ {_now_beijing()}\n🔴 Obsidian Clip API 已关闭")
    # 等待通知发送完成
    time.sleep(2)


app = FastAPI(
    title="Obsidian Clip API",
    description="网页剪藏 API 服务",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """根路径，返回服务信息"""
    return {
        "name": config.get("name"),
        "version": config.get("version"),
        "description": config.get("description")
    }

"""
Obsidian Clip API 主入口模块

提供网页剪藏到 Obsidian 的 API 服务。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router
from .config import config
from .logger import logger, setup_logger

# 根据配置初始化日志系统（启用颜色）
setup_logger(debug=config.debug, colorize=True)

app = FastAPI(
    title="Obsidian Clip API",
    description="网页剪藏 API 服务",
    version="1.0.0"
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

@app.on_event("startup")
async def startup_event():
    """服务启动时的初始化"""
    logger.info(f"[API] Obsidian Clip API 服务启动")
    logger.info(f"[API] 存储方式: {config.storage_method}")
    logger.info(f"[API] 图床功能: {'启用' if config.get('picgo.enabled', False) else '禁用'}")
    logger.info(f"[API] LLM 处理: {'启用' if config.llm_enabled else '禁用'}")


@app.get("/")
async def root():
    """根路径，返回服务信息"""
    return {
        "name": config.get("name"),
        "version": config.get("version"),
        "description": config.get("description")
    } 
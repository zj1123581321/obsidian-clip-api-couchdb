"""
统一日志配置模块

使用 loguru 实现统一的日志格式，支持：
- 控制台输出（带颜色）
- 文件输出（自动轮转）
- 错误日志单独存储
- 拦截标准 logging 输出

输出格式：2026-01-12 14:48:20 | INFO     | app.services.llm_service:process:128 - [LLM] 处理完成
"""

import os
import sys
import logging
import io
from pathlib import Path
from loguru import logger

# 修复 Windows 控制台中文编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 日志目录配置
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class InterceptHandler(logging.Handler):
    """拦截标准 logging 输出并转发到 loguru"""

    def emit(self, record: logging.LogRecord) -> None:
        """处理日志记录

        Args:
            record: 标准 logging 的日志记录
        """
        # 获取对应的 loguru 级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 查找调用者的堆栈帧
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# 日志格式配置
LOG_FORMAT_CONSOLE = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

LOG_FORMAT_FILE = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} - "
    "{message}"
)


def setup_logger(
    debug: bool = False,
    colorize: bool = True,
    log_dir: Path = LOG_DIR,
    rotation: str = "10 MB",
    retention: str = "30 days",
    compression: str = "zip",
) -> None:
    """配置日志系统

    Args:
        debug: 是否开启调试模式，开启后输出 DEBUG 级别日志
        colorize: 是否启用彩色输出
        log_dir: 日志文件目录
        rotation: 日志轮转策略，支持大小（如 "10 MB"）或时间（如 "1 day"）
        retention: 日志保留时间
        compression: 压缩格式（zip, gz, bz2, xz, tar 等）
    """
    # 确保日志目录存在
    log_dir.mkdir(exist_ok=True)

    # 移除所有现有的 loguru handler
    logger.remove()

    # 日志级别
    level = "DEBUG" if debug else "INFO"

    # 1. 控制台输出（带颜色）
    logger.add(
        sys.stderr,
        format=LOG_FORMAT_CONSOLE,
        level=level,
        colorize=colorize,
        backtrace=True,
        diagnose=debug,
        enqueue=True,
    )

    # 2. 主日志文件（所有级别）
    logger.add(
        log_dir / "app.log",
        format=LOG_FORMAT_FILE,
        level=level,
        rotation=rotation,
        retention=retention,
        compression=compression,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=debug,
    )

    # 3. 错误日志文件（仅 WARNING 及以上级别）
    logger.add(
        log_dir / "error.log",
        format=LOG_FORMAT_FILE,
        level="WARNING",
        rotation=rotation,
        retention=retention,
        compression=compression,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,  # 错误日志始终显示详细诊断信息
    )

    # 拦截标准 logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 配置 uvicorn 相关的 logger
    for logger_name in [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
    ]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False


# 默认初始化（启用颜色）
setup_logger(debug=False, colorize=True)

# 导出 logger 实例供其他模块使用
__all__ = ["logger", "setup_logger", "LOG_DIR"]

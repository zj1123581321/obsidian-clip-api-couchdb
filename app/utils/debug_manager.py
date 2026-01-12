"""
统一的 Debug 文件管理模块

提供按任务时间戳创建子文件夹的功能，集中管理所有调试文件的保存逻辑。
每次剪藏任务会在 debug 目录下创建一个以时间戳命名的子文件夹。
"""

import os
from datetime import datetime
from typing import Optional
from ..config import config
from ..logger import logger


class DebugManager:
    """Debug 文件管理器

    管理调试文件的保存，每次任务创建独立的时间戳子文件夹。

    Attributes:
        base_dir: 调试文件的基础目录
        session_dir: 当前任务的调试文件目录
        file_seq: 文件序号计数器
    """

    def __init__(self, base_dir: str = "debug"):
        """初始化 Debug 管理器

        Args:
            base_dir: 调试文件的基础目录，默认为 "debug"
        """
        self.base_dir = base_dir
        self.session_dir: Optional[str] = None
        self.file_seq = 1

    def start_session(self, task_id: Optional[str] = None) -> str:
        """开始新的调试会话，创建时间戳子文件夹

        每次剪藏任务开始时调用此方法，创建独立的调试目录。

        Args:
            task_id: 可选的任务标识，如果不提供则使用时间戳

        Returns:
            str: 创建的会话目录路径
        """
        if not config.debug:
            return ""

        # 生成时间戳格式的文件夹名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{timestamp}_{task_id}" if task_id else timestamp

        self.session_dir = os.path.join(self.base_dir, folder_name)
        self.file_seq = 1

        try:
            os.makedirs(self.session_dir, exist_ok=True)
            logger.debug(f"[DEBUG] 创建调试会话目录: {self.session_dir}")
        except Exception as e:
            logger.warning(f"[DEBUG] 创建调试会话目录失败: {e}")

        return self.session_dir

    def end_session(self) -> None:
        """结束当前调试会话

        重置会话目录和文件序号。
        """
        self.session_dir = None
        self.file_seq = 1
        logger.debug("[DEBUG] 调试会话结束")

    def get_session_dir(self) -> Optional[str]:
        """获取当前会话目录

        Returns:
            Optional[str]: 当前会话目录路径，未开始会话时返回 None
        """
        return self.session_dir

    def save_file(self, filename: str, content: str, prefix: str = "") -> Optional[str]:
        """保存调试文件

        Args:
            filename: 文件名（不含序号前缀）
            content: 文件内容
            prefix: 可选的文件名前缀，用于标识来源模块

        Returns:
            Optional[str]: 保存成功返回文件路径，失败或未启用 debug 返回 None
        """
        if not config.debug:
            return None

        # 如果没有会话目录，使用基础目录（向后兼容）
        target_dir = self.session_dir if self.session_dir else self.base_dir

        try:
            os.makedirs(target_dir, exist_ok=True)

            # 添加序号前缀
            base, ext = os.path.splitext(filename)
            if prefix:
                full_filename = f"{self.file_seq:02d}_{prefix}_{base}{ext}"
            else:
                full_filename = f"{self.file_seq:02d}_{base}{ext}"
            self.file_seq += 1

            filepath = os.path.join(target_dir, full_filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.debug(f"[DEBUG] 已保存调试文件: {filepath}")
            return filepath

        except Exception as e:
            logger.warning(f"[DEBUG] 保存调试文件失败: {e}")
            return None

    def save_binary_file(
        self,
        filename: str,
        content: bytes,
        prefix: str = ""
    ) -> Optional[str]:
        """保存二进制调试文件（如图片）

        Args:
            filename: 文件名（不含序号前缀）
            content: 二进制内容
            prefix: 可选的文件名前缀

        Returns:
            Optional[str]: 保存成功返回文件路径，失败或未启用 debug 返回 None
        """
        if not config.debug:
            return None

        target_dir = self.session_dir if self.session_dir else self.base_dir

        try:
            os.makedirs(target_dir, exist_ok=True)

            # 添加序号前缀
            base, ext = os.path.splitext(filename)
            if prefix:
                full_filename = f"{self.file_seq:02d}_{prefix}_{base}{ext}"
            else:
                full_filename = f"{self.file_seq:02d}_{base}{ext}"
            self.file_seq += 1

            filepath = os.path.join(target_dir, full_filename)
            with open(filepath, 'wb') as f:
                f.write(content)

            logger.debug(f"[DEBUG] 已保存二进制调试文件: {filepath}")
            return filepath

        except Exception as e:
            logger.warning(f"[DEBUG] 保存二进制调试文件失败: {e}")
            return None


# 全局单例实例
debug_manager = DebugManager()

# 导出
__all__ = ["debug_manager", "DebugManager"]

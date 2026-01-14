"""
通知服务模块

负责发送企业微信通知和控制台日志输出。
使用 wecom-notifier 包实现群机器人 Webhook 消息发送。
"""

from typing import Optional
from ..config import config
from ..logger import logger

# 延迟导入 wecom-notifier，避免未安装时启动失败
_wecom_notifier: Optional["WeComNotifier"] = None


def _get_notifier():
    """获取全局 WeComNotifier 实例（单例模式）

    Returns:
        WeComNotifier 实例，如果未启用或配置不完整则返回 None
    """
    global _wecom_notifier

    if _wecom_notifier is not None:
        return _wecom_notifier

    if not config.work_wechat_enabled:
        return None

    if not config.work_wechat_webhook_url:
        logger.warning("[WeChat] webhook_url 未配置，企业微信通知已禁用")
        return None

    try:
        from wecom_notifier import WeComNotifier
        _wecom_notifier = WeComNotifier(max_retries=3, retry_delay=2.0)
        logger.info("[WeChat] 企业微信通知服务已初始化")
        return _wecom_notifier
    except ImportError:
        logger.warning("[WeChat] wecom-notifier 包未安装，企业微信通知已禁用")
        return None
    except Exception as e:
        logger.error(f"[WeChat] 初始化 WeComNotifier 失败: {e}")
        return None


class NotificationService:
    """企业微信通知服务

    使用 wecom-notifier 包通过群机器人 Webhook 发送消息。
    保持与旧接口兼容，对调用方透明。
    """

    def __init__(self):
        self.webhook_url = config.work_wechat_webhook_url
        self.at_all = config.work_wechat_at_all

    def send_message(self, content: str, msg_type: str = "text"):
        """发送企业微信消息

        Args:
            content: 消息内容
            msg_type: 消息类型，支持 "text" 或 "markdown"
        """
        notifier = _get_notifier()
        if notifier is None:
            logger.debug(f"[WeChat] 通知服务未启用，消息未发送: {content[:50]}...")
            return

        try:
            if msg_type == "markdown":
                result = notifier.send_markdown(
                    webhook_url=self.webhook_url,
                    content=content,
                    mention_all=self.at_all,
                    async_send=True
                )
            else:
                mentioned_list = ["@all"] if self.at_all else None
                result = notifier.send_text(
                    webhook_url=self.webhook_url,
                    content=content,
                    mentioned_list=mentioned_list,
                    async_send=True
                )

            logger.debug(f"[WeChat] 消息已提交发送队列")

        except Exception as e:
            logger.error(f"[WeChat] 发送消息异常: {e}")

    def send_markdown(self, content: str):
        """发送 Markdown 格式消息

        Args:
            content: Markdown 格式的消息内容
        """
        self.send_message(content, msg_type="markdown")

    def send_progress(self, title: str, message: str):
        """发送进度信息（仅打印到控制台）

        Args:
            title: 进度标题
            message: 进度消息
        """
        logger.info(f"[{title}] {message}")

    def send_success(self, title: str, message: str):
        """发送成功信息（同时发送到企业微信，使用 Markdown 格式）

        Args:
            title: 成功标题
            message: 成功消息
        """
        logger.info(f"[Success] {title}: {message}")

        # 使用 Markdown 格式美化消息
        markdown_content = f"""## {title}

{message}"""
        self.send_markdown(markdown_content)

    def send_error(self, message: str):
        """发送错误信息（同时发送到企业微信）

        Args:
            message: 错误消息
        """
        logger.error(f"[Error] {message}")

        # 使用 Markdown 格式美化错误消息
        markdown_content = f"""## 错误

{message}"""
        self.send_markdown(markdown_content)

    def send_clip_start(self, url: str, picgo_enabled: bool = False):
        """发送剪藏开始通知

        Args:
            url: 剪藏的 URL
            picgo_enabled: 图床是否启用
        """
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        picgo_status = "已启用" if picgo_enabled else "未启用"

        markdown_content = f"""## 开始剪藏

**时间**: {now}
**链接**: {url}
**图床**: {picgo_status}"""

        self.send_markdown(markdown_content)

    def send_clip_success(
        self,
        title: str,
        url: str,
        doc_path: str,
        category: str = None,
        processing_time: float = None
    ):
        """发送剪藏成功通知

        Args:
            title: 文章标题
            url: 原文链接
            doc_path: 保存路径
            category: LLM 分类结果（可选）
            processing_time: 处理耗时（可选）
        """
        lines = [
            "## 剪藏成功",
            "",
            f"**标题**: {title}",
            f"**链接**: {url}",
            f"**路径**: {doc_path}",
        ]

        if category:
            lines.append(f"**分类**: {category}")

        if processing_time is not None:
            lines.append(f"**耗时**: {processing_time:.1f}s")

        markdown_content = "\n".join(lines)
        self.send_markdown(markdown_content)


# 创建全局通知服务实例
notifier = NotificationService()

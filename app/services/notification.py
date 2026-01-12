"""
通知服务模块

负责发送企业微信通知和控制台日志输出。
"""

import requests
import time
from ..config import config
from ..logger import logger


class NotificationService:
    """企业微信通知服务"""

    def __init__(self):
        self.corp_id = config.work_wechat_corp_id
        self.agent_id = config.work_wechat_agent_id
        self.corp_secret = config.work_wechat_corp_secret
        self.access_token = None
        self.token_expires = 0

    def _get_access_token(self) -> str:
        """获取企业微信访问令牌

        Returns:
            str: 访问令牌

        Raises:
            Exception: 获取令牌失败时抛出异常
        """
        if self.access_token and time.time() < self.token_expires:
            return self.access_token

        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
        response = requests.get(url)
        result = response.json()

        if result.get('errcode') == 0:
            self.access_token = result['access_token']
            self.token_expires = time.time() + result['expires_in'] - 200
            return self.access_token
        else:
            raise Exception(f"获取企业微信访问令牌失败: {result}")

    def send_message(self, content: str, msg_type: str = "text"):
        """发送企业微信消息

        Args:
            content: 消息内容
            msg_type: 消息类型，默认为 text
        """
        if not self.corp_id or not self.agent_id or not self.corp_secret:
            logger.info(f"[WeChat] 配置不完整，消息未发送: {content}")
            return

        try:
            access_token = self._get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

            data = {
                "touser": "@all" if config.work_wechat_at_all else config.work_wechat_user_id,
                "msgtype": msg_type,
                "agentid": self.agent_id,
                "text": {
                    "content": content
                }
            }

            response = requests.post(url, json=data)
            result = response.json()

            if result.get('errcode') != 0:
                logger.warning(f"[WeChat] 发送消息失败: {result}")

        except Exception as e:
            logger.error(f"[WeChat] 发送消息异常: {str(e)}")

    def send_progress(self, title: str, message: str):
        """发送进度信息（仅打印到控制台）

        Args:
            title: 进度标题
            message: 进度消息
        """
        logger.info(f"[{title}] {message}")

    def send_success(self, title: str, message: str):
        """发送成功信息（同时发送到企业微信）

        Args:
            title: 成功标题
            message: 成功消息
        """
        logger.info(f"[Success] {title}: {message}")
        self.send_message(f"{title}\n{message}")

    def send_error(self, message: str):
        """发送错误信息（同时发送到企业微信）

        Args:
            message: 错误消息
        """
        logger.error(f"[Error] {message}")
        self.send_message(f"错误\n{message}")


# 创建全局通知服务实例
notifier = NotificationService()

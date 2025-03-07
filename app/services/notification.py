import requests
import json
from ..config import config
import time

class NotificationService:
    def __init__(self):
        self.corp_id = config.work_wechat_corp_id
        self.agent_id = config.work_wechat_agent_id
        self.corp_secret = config.work_wechat_corp_secret
        self.access_token = None
        self.token_expires = 0

    def _get_access_token(self) -> str:
        """获取企业微信访问令牌"""
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

    def _send_message(self, content: str, msg_type: str = "text"):
        """发送企业微信消息"""
        if not self.corp_id or not self.agent_id or not self.corp_secret:
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
                print(f"发送企业微信消息失败: {result}")
                
        except Exception as e:
            print(f"发送企业微信消息异常: {str(e)}")

    def send_progress(self, title: str, message: str):
        """发送进度信息（仅打印到控制台）"""
        print(f"[{title}] {message}")

    def send_success(self, title: str, message: str):
        """发送成功信息（同时发送到企业微信）"""
        print(f"[成功] {title}: {message}")
        self._send_message(f"✅ {title}\n{message}")

    def send_error(self, message: str):
        """发送错误信息（同时发送到企业微信）"""
        print(f"[错误] {message}")
        self._send_message(f"❌ 错误\n{message}")

# 创建全局通知服务实例
notifier = NotificationService() 
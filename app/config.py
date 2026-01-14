import os
import yaml
from typing import Dict, Any

class Config:
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self):
        config_path = os.getenv('CONFIG_PATH', 'config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项，支持点号分隔的键名"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value

    @property
    def couchdb_url(self) -> str:
        return self.get('couchdb.url')

    @property
    def couchdb_db_name(self) -> str:
        return self.get('couchdb.db_name')

    @property
    def work_wechat_enabled(self) -> bool:
        """是否启用企业微信通知"""
        return self.get('work_wechat.enabled', False)

    @property
    def work_wechat_webhook_url(self) -> str:
        """企业微信群机器人 Webhook URL"""
        return self.get('work_wechat.webhook_url', '')

    @property
    def work_wechat_at_all(self) -> bool:
        """发送消息时是否 @所有人"""
        return self.get('work_wechat.at_all', False)

    @property
    def picgo_server(self) -> str:
        return self.get('picgo.server')

    @property
    def picgo_upload_path(self) -> str:
        return self.get('picgo.upload_path')

    @property
    def debug(self) -> bool:
        return self.get('debug', False)

    # 新增：存储方式配置
    @property
    def storage_method(self) -> str:
        """获取存储方式：couchdb 或 rest_api"""
        return self.get('storage.method', 'rest_api')

    # 新增：Obsidian REST API 配置
    @property
    def obsidian_api_url(self) -> str:
        return self.get('obsidian_api.url', 'http://127.0.0.1:27123')

    @property
    def obsidian_api_key(self) -> str:
        return self.get('obsidian_api.api_key')

    @property
    def obsidian_api_timeout(self) -> int:
        return self.get('obsidian_api.timeout', 30)

    @property
    def obsidian_api_retry_count(self) -> int:
        return self.get('obsidian_api.retry_count', 3)

    @property
    def obsidian_api_retry_delay(self) -> int:
        return self.get('obsidian_api.retry_delay', 1)

    # 新增：Obsidian 文件配置
    @property
    def obsidian_clippings_path(self) -> str:
        return self.get('obsidian.clippings_path', 'Clippings')

    @property
    def obsidian_date_folder(self) -> bool:
        return self.get('obsidian.date_folder', True)

    # LLM 处理配置
    @property
    def llm_enabled(self) -> bool:
        """是否启用 LLM 处理，默认开启"""
        return self.get('llm.enabled', True)

    @property
    def llm_url(self) -> str:
        """LLM API 地址"""
        return self.get('llm.url', '')

    @property
    def llm_api_key(self) -> str:
        """LLM API 密钥"""
        return self.get('llm.api_key', '')

    @property
    def llm_timeout(self) -> int:
        """LLM API 超时时间（秒），默认 300"""
        return self.get('llm.timeout', 300)

    @property
    def llm_retry_count(self) -> int:
        """LLM API 重试次数，默认 2"""
        return self.get('llm.retry_count', 2)

    @property
    def llm_retry_delay(self) -> int:
        """LLM API 重试延迟（秒），默认 2"""
        return self.get('llm.retry_delay', 2)

    @property
    def llm_language(self) -> str:
        """LLM 处理语言，默认 auto"""
        return self.get('llm.language', 'auto')

    # 日志配置
    @property
    def log_level(self) -> str:
        """日志级别，默认 INFO"""
        return self.get('logging.level', 'INFO')

    @property
    def log_colorize(self) -> bool:
        """是否启用彩色日志输出，默认 True"""
        return self.get('logging.colorize', True)

    @property
    def log_rotation(self) -> str:
        """日志轮转策略，默认 10 MB"""
        return self.get('logging.rotation', '10 MB')

    @property
    def log_retention(self) -> str:
        """日志保留时间，默认 30 days"""
        return self.get('logging.retention', '30 days')

    @property
    def log_compression(self) -> str:
        """日志压缩格式，默认 zip"""
        return self.get('logging.compression', 'zip')


config = Config()
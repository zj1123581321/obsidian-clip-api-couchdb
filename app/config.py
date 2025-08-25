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
    def work_wechat_corp_id(self) -> str:
        return self.get('work_wechat.corp_id')

    @property
    def work_wechat_agent_id(self) -> str:
        return self.get('work_wechat.agent_id')

    @property
    def work_wechat_corp_secret(self) -> str:
        return self.get('work_wechat.corp_secret')

    @property
    def work_wechat_token(self) -> str:
        return self.get('work_wechat.token')

    @property
    def work_wechat_encoding_aes_key(self) -> str:
        return self.get('work_wechat.encoding_aes_key')

    @property
    def work_wechat_user_id(self) -> str:
        return self.get('work_wechat.user_id')

    @property
    def work_wechat_at_all(self) -> bool:
        return self.get('work_wechat.at_all', True)

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

config = Config() 
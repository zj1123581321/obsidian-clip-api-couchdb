import couchdb
import time
import base64
from typing import Optional, Tuple
from ..config import config
from ..services.notification import notifier

class CouchDBService:
    def __init__(self):
        self.server = couchdb.Server(config.couchdb_url)
        self.db = self.server[config.couchdb_db_name]

    def _generate_leaf_id(self) -> str:
        """生成叶子节点 ID"""
        timestamp = int(time.time() * 1000)
        return f"h:{timestamp}"

    def _create_leaf_doc(self, content: str) -> Tuple[str, str]:
        """创建叶子节点文档"""
        leaf_id = self._generate_leaf_id()
        leaf_doc = {
            "_id": leaf_id,
            "data": content,
            "type": "leaf"
        }
        leaf_id, leaf_rev = self.db.save(leaf_doc)
        return leaf_id, leaf_rev

    def _create_parent_doc(self, file_key: str, leaf_id: str, content: str) -> str:
        """创建父节点文档"""
        now = int(time.time() * 1000)
        parent_doc = {
            "_id": file_key.lower(),  # 使用小写的文件路径作为 ID
            "path": file_key,  # 保持原始路径大小写
            "children": [leaf_id],
            "ctime": now,
            "mtime": now,
            "size": len(content),
            "type": "plain",
            "deleted": False,
            "eden": {}
        }
        parent_id, _ = self.db.save(parent_doc)
        return parent_id

    def save_document(self, title: str, content: str, url: str) -> Optional[str]:
        """保存文档到 CouchDB"""
        try:
            notifier.send_progress("保存文档", "正在保存到 CouchDB")
            
            # 生成文件路径
            timestamp = time.strftime("%Y%m%d%H%M")
            file_key = f"HtmlPages/{timestamp} {title}.md"
            
            # 创建叶子节点
            leaf_id, _ = self._create_leaf_doc(content)
            
            # 创建父节点
            parent_id = self._create_parent_doc(file_key, leaf_id, content)
            
            notifier.send_progress("文档保存成功", f"文档 ID: {parent_id}")
            return parent_id
            
        except Exception as e:
            error_msg = f"保存文档失败: {str(e)}"
            notifier.send_error(error_msg)
            raise Exception(error_msg)

# 创建全局 CouchDB 服务实例
couchdb_service = CouchDBService() 
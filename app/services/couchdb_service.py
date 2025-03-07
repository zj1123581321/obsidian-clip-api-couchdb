import couchdb
import time
from datetime import datetime
import os
from typing import Optional, Tuple
from ..config import config
from ..services.notification import notifier

class CouchDBService:
    def __init__(self):
        self.server = couchdb.Server(config.couchdb_url)
        self.db = self.server[config.couchdb_db_name]
        # 获取配置的剪藏路径，默认为 "Clippings"
        self.clippings_path = config.get('obsidian', {}).get('clippings_path', 'Clippings')
        # 确保路径不以斜杠开头或结尾
        self.clippings_path = self.clippings_path.strip('/')

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

    def _generate_file_path(self, title: str) -> str:
        """生成文件路径
        
        Args:
            title: 文章标题
            
        Returns:
            str: 生成的文件路径，格式为：Clippings/YYMMDD_HHMM_标题.md
        """
        # 生成时间戳：YYMMDD_HHMM
        timestamp = datetime.now().strftime("%y%m%d_%H%M")
        # 清理文件名中的非法字符
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        # 如果标题太长，截断它
        if len(safe_title) > 50:
            safe_title = safe_title[:47] + "..."
        # 组合文件名：时间戳_标题.md
        filename = f"{timestamp}_{safe_title}.md"
        # 返回完整路径（不带开头的斜杠）
        return f"{self.clippings_path}/{filename}"

    def save_document(self, title: str, content: str, url: str) -> Optional[str]:
        """保存文档到 CouchDB"""
        try:
            notifier.send_progress("保存文档", "正在保存到 CouchDB")
            
            # 生成文件路径
            file_key = self._generate_file_path(title)
            
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

    def get_document_path(self, doc_id: str) -> str:
        """获取文档的保存路径
        
        Args:
            doc_id: 文档ID
            
        Returns:
            str: 文档的保存路径
        """
        try:
            doc = self.db.get(doc_id)
            return doc.get('path', '')
        except Exception as e:
            self._log(f"获取文档路径失败: {str(e)}")
            return ''

# 创建全局 CouchDB 服务实例
couchdb_service = CouchDBService() 
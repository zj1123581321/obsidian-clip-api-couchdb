import aiohttp
import asyncio
import re
from datetime import datetime
from typing import Optional, Dict, Any
from ..config import config
from ..services.notification import notifier


class ObsidianRestAPIService:
    """Obsidian Local REST API 服务类"""
    
    def __init__(self):
        self.base_url = config.get('obsidian_api.url', 'http://127.0.0.1:27123')
        self.api_key = config.get('obsidian_api.api_key')
        self.timeout = config.get('obsidian_api.timeout', 30)
        self.retry_count = config.get('obsidian_api.retry_count', 3)
        self.retry_delay = config.get('obsidian_api.retry_delay', 1)
        
        # URL 验证和规范化
        self.base_url = self._normalize_url(self.base_url)
        
        # 获取文件路径配置
        self.clippings_path = config.get('obsidian.clippings_path', 'Clippings')
        self.date_folder = config.get('obsidian.date_folder', True)
        
        # 确保路径不以斜杠开头或结尾
        self.clippings_path = self.clippings_path.strip('/')

    def _normalize_url(self, url: str) -> str:
        """规范化和验证 URL
        
        Args:
            url: 原始 URL
            
        Returns:
            str: 规范化后的 URL
        """
        if not url:
            raise ValueError("Obsidian API URL 不能为空")
        
        # 确保 URL 以 http:// 或 https:// 开头
        if not url.startswith(('http://', 'https://')):
            url = f'http://{url}'
        
        # 将 0.0.0.0 替换为 127.0.0.1（避免连接问题）
        url = url.replace('://0.0.0.0:', '://127.0.0.1:')
        
        # 移除末尾的斜杠
        url = url.rstrip('/')
        
        return url

    def _sanitize_filename(self, title: str) -> str:
        """清理文件名，移除不安全字符
        
        Args:
            title: 原始标题
            
        Returns:
            str: 清理后的标题，适用于文件名
        """
        # 移除或替换不安全的文件名字符
        title = re.sub(r'[<>:"/\\|?*]', '', title)  # 移除完全不允许的字符
        title = re.sub(r'\s+', '_', title.strip())  # 替换空白字符为下划线
        title = re.sub(r'[^\w\u4e00-\u9fff._-]', '', title)  # 只保留字母、数字、中文、下划线、点和横线
        
        # 限制长度，为时间戳和扩展名预留空间
        if len(title) > 100:
            title = title[:100]
            
        return title or 'untitled'

    def generate_file_path(self, title: str) -> str:
        """生成文件路径
        
        Args:
            title: 文章标题
            
        Returns:
            str: 完整的文件路径
        """
        now = datetime.now()
        
        # 生成文件名：yyyymmdd_hhmm_{title}.md
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M")
        sanitized_title = self._sanitize_filename(title)
        filename = f"{date_str}_{time_str}_{sanitized_title}.md"
        
        # 构建完整路径
        path_parts = [self.clippings_path]
        
        # 可选的日期文件夹：year/month
        if self.date_folder:
            year = now.strftime("%Y")
            month = now.strftime("%m")
            path_parts.extend([year, month])
        
        path_parts.append(filename)
        
        # 使用正斜杠作为路径分隔符（Obsidian 标准）
        return '/'.join(path_parts)

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> aiohttp.ClientResponse:
        """发送 HTTP 请求到 Obsidian REST API
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: 其他请求参数
            
        Returns:
            aiohttp.ClientResponse: 响应对象
            
        Raises:
            Exception: 网络或 API 错误
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': '*/*',
            **kwargs.pop('headers', {})
        }
        
        # 记录请求详情（调试模式）
        if config.debug:
            notifier.send_progress("调试", f"发送请求: {method} {url}")
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method, url, headers=headers, **kwargs) as response:
                    return response
        except aiohttp.ClientConnectorError as e:
            raise Exception(f"无法连接到 Obsidian REST API ({url}): {str(e)}")
        except asyncio.TimeoutError:
            raise Exception(f"Obsidian REST API 请求超时 (超过 {self.timeout} 秒)")
        except Exception as e:
            raise Exception(f"Obsidian REST API 请求失败: {str(e)}")

    async def _handle_api_error(self, response: aiohttp.ClientResponse, file_path: str) -> None:
        """处理 API 错误响应
        
        Args:
            response: HTTP 响应对象
            file_path: 尝试创建的文件路径
        """
        status = response.status
        
        try:
            error_data = await response.json()
            error_message = error_data.get('message', '未知错误')
        except:
            error_message = await response.text() or f'HTTP {status} 错误'
        
        if status == 401:
            raise Exception(f"Obsidian REST API 认证失败，请检查 API Key 配置")
        elif status == 400:
            raise Exception(f"文件创建失败：{error_message}")
        elif status == 405:
            raise Exception(f"文件创建失败：路径 '{file_path}' 指向目录而非文件")
        elif status == 404:
            raise Exception(f"Obsidian REST API 端点不存在，请检查 URL 配置")
        else:
            raise Exception(f"Obsidian API 请求失败 (HTTP {status}): {error_message}")

    async def save_document(self, title: str, content: str, url: str) -> str:
        """保存文档到 Obsidian
        
        Args:
            title: 文档标题
            content: 文档内容（包含 YAML front matter）
            url: 原文链接
            
        Returns:
            str: 保存的文件路径
            
        Raises:
            Exception: 保存失败时抛出异常
        """
        file_path = self.generate_file_path(title)
        
        for attempt in range(self.retry_count + 1):
            try:
                notifier.send_progress("文档保存", f"正在保存到 Obsidian: {file_path}")
                
                # 直接在这里处理请求和响应
                request_url = f"{self.base_url}/vault/{file_path}"
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'text/markdown',
                    'Accept': '*/*'
                }
                
                if config.debug:
                    notifier.send_progress("调试", f"PUT {request_url}")
                
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.put(
                        request_url, 
                        headers=headers, 
                        data=content.encode('utf-8')
                    ) as response:
                        if response.status == 204:
                            # 成功创建文件
                            return file_path
                        else:
                            # 处理错误响应
                            try:
                                error_data = await response.json()
                                error_message = error_data.get('message', '未知错误')
                            except:
                                error_message = await response.text() or f'HTTP {response.status} 错误'
                            
                            if response.status == 401:
                                raise Exception(f"Obsidian REST API 认证失败，请检查 API Key 配置")
                            elif response.status == 400:
                                raise Exception(f"文件创建失败：{error_message}")
                            elif response.status == 405:
                                raise Exception(f"文件创建失败：路径 '{file_path}' 指向目录而非文件")
                            elif response.status == 404:
                                raise Exception(f"Obsidian REST API 端点不存在，请检查 URL 配置")
                            else:
                                raise Exception(f"Obsidian API 请求失败 (HTTP {response.status}): {error_message}")
                    
            except aiohttp.ClientError as e:
                # 网络相关错误
                if attempt < self.retry_count:
                    wait_time = self.retry_delay * (2 ** attempt)  # 指数退避
                    notifier.send_progress("重试", f"网络错误，{wait_time}秒后重试 ({attempt + 1}/{self.retry_count})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"无法连接到 Obsidian REST API: {str(e)}")
                    
            except Exception as e:
                # 其他错误（认证、业务逻辑等），不重试
                raise e
        
        # 不应该到达这里
        raise Exception("文档保存失败：超过最大重试次数")

    async def health_check(self) -> bool:
        """检查 Obsidian REST API 服务状态
        
        Returns:
            bool: 服务是否可用
        """
        try:
            connection_info = await self.test_connection()
            return connection_info['status'] == 'connected'
        except:
            return False

    async def test_connection(self) -> Dict[str, Any]:
        """测试连接并返回服务信息
        
        Returns:
            dict: 包含连接状态和服务信息的字典
        """
        try:
            request_url = f"{self.base_url}/"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json'
            }
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(request_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'status': 'connected',
                            'authenticated': data.get('authenticated', False),
                            'service': data.get('service', 'Unknown'),
                            'version': data.get('versions', {}).get('self', 'Unknown'),
                            'url': request_url
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'status': 'error',
                            'error': f'HTTP {response.status}: {error_text}',
                            'authenticated': False,
                            'url': request_url
                        }
                
        except aiohttp.ClientError as e:
            return {
                'status': 'connection_failed',
                'error': str(e),
                'authenticated': False,
                'url': getattr(self, 'base_url', 'unknown')
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'authenticated': False,
                'url': getattr(self, 'base_url', 'unknown')
            }

    def get_document_path(self, file_path: str) -> str:
        """获取文档在 Obsidian 中的显示路径
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 适合显示的文档路径
        """
        return file_path


# 创建全局实例
obsidian_rest_api = ObsidianRestAPIService()
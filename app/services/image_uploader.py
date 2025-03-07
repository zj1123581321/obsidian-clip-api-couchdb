import aiohttp
import asyncio
from typing import List, Tuple, Dict
import os
import json
import tempfile
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
from ..config import config
from ..services.notification import notifier
import re

class ImageUploader:
    def __init__(self):
        self.picgo_server = config.picgo_server
        self.upload_path = config.picgo_upload_path
        self.debug_dir = "debug"
        self.debug_seq = 1  # 调试文件序号

    def _log(self, message: str):
        """输出带时间戳的日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"[{timestamp}] {message}")

    def _save_debug_file(self, filename: str, content: str):
        """保存调试文件"""
        if config.debug:
            try:
                os.makedirs(self.debug_dir, exist_ok=True)
                # 添加序号前缀
                base, ext = os.path.splitext(filename)
                filename = f"{self.debug_seq:02d}_{base}{ext}"
                self.debug_seq += 1
                
                filepath = os.path.join(self.debug_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                self._log(f"已保存调试文件: {filename}")
            except Exception as e:
                self._log(f"保存调试文件失败: {str(e)}")

    def _save_debug_image(self, filename: str, content: bytes):
        """保存调试图片文件"""
        if config.debug:
            try:
                os.makedirs(self.debug_dir, exist_ok=True)
                # 添加序号前缀
                base, ext = os.path.splitext(filename)
                filename = f"{self.debug_seq:02d}_{base}{ext}"
                self.debug_seq += 1
                
                filepath = os.path.join(self.debug_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(content)
                self._log(f"已保存调试图片: {filename}")
            except Exception as e:
                self._log(f"保存调试图片失败: {str(e)}")

    async def _download_image(self, session: aiohttp.ClientSession, image_url: str) -> bytes:
        """下载图片"""
        start_time = time.time()
        self._log(f"开始下载图片: {image_url}")
        try:
            async with session.get(image_url) as response:
                if response.status != 200:
                    raise Exception(f"下载失败，状态码: {response.status}")
                
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    raise Exception(f"非图片类型: {content_type}")
                
                image_data = await response.read()
                elapsed = time.time() - start_time
                self._log(f"图片下载成功: {len(image_data)} 字节，耗时: {elapsed:.2f}秒")
                return image_data
        except Exception as e:
            self._log(f"下载图片失败: {str(e)}")
            raise

    async def _upload_to_picgo(self, session: aiohttp.ClientSession, 
                             image_data: bytes, filename: str) -> str:
        """上传图片到 PicGo"""
        start_time = time.time()
        self._log(f"开始上传图片到 PicGo: {filename}")
        
        max_retries = 3  # 最大重试次数
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 准备上传表单
                form = aiohttp.FormData()
                form.add_field('image', 
                             image_data,
                             filename=filename,
                             content_type='image/jpeg')

                # 构建完整的上传 URL
                upload_url = urljoin(self.picgo_server, self.upload_path)
                self._log(f"上传 URL: {upload_url}")

                # 发送上传请求，添加超时
                timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
                async with session.post(upload_url, data=form, timeout=timeout) as response:
                    if response.status != 200:
                        raise Exception(f"上传失败，状态码: {response.status}")
                    
                    result = await response.json()
                    self._log(f"PicGo 响应: {json.dumps(result, ensure_ascii=False)}")

                    if not result.get('success'):
                        raise Exception(f"上传失败: {result.get('msg')}")
                    
                    if not result.get('result'):
                        raise Exception("上传成功但未返回 URL")
                    
                    new_url = result['result'][0]
                    elapsed = time.time() - start_time
                    self._log(f"图片上传成功: {new_url}，耗时: {elapsed:.2f}秒")
                    return new_url

            except asyncio.TimeoutError:
                retry_count += 1
                if retry_count < max_retries:
                    self._log(f"上传超时，正在进行第 {retry_count} 次重试...")
                    await asyncio.sleep(2)  # 等待2秒后重试
                else:
                    raise Exception("上传多次超时，放弃重试")
                    
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    self._log(f"上传失败: {str(e)}，正在进行第 {retry_count} 次重试...")
                    await asyncio.sleep(2)  # 等待2秒后重试
                else:
                    raise Exception(f"上传失败并超过最大重试次数: {str(e)}")

    async def _process_single_image(self, session: aiohttp.ClientSession, 
                                  image_url: str, alt: str) -> Tuple[str, str]:
        """处理单张图片的下载和上传"""
        start_time = time.time()
        try:
            # 生成文件名
            url_parts = urlparse(image_url)
            original_filename = os.path.basename(url_parts.path) or 'image.jpg'
            filename = f"{alt}_{original_filename}" if alt else original_filename

            # 下载图片
            image_data = await self._download_image(session, image_url)

            # 保存调试文件
            if config.debug:
                debug_path = os.path.join(self.debug_dir, f"debug_image_{filename}")
                os.makedirs(self.debug_dir, exist_ok=True)
                with open(debug_path, 'wb') as f:
                    f.write(image_data)
                self._log(f"已保存调试图片: {debug_path}")

            # 上传到图床
            new_url = await self._upload_to_picgo(session, image_data, filename)
            elapsed = time.time() - start_time
            self._log(f"单张图片处理完成，总耗时: {elapsed:.2f}秒")
            return image_url, new_url

        except Exception as e:
            self._log(f"处理图片失败: {str(e)}")
            return image_url, image_url

    async def upload_images(self, images: List[Tuple[str, str]]) -> Dict[str, str]:
        """并发上传所有图片"""
        if not images:
            return {}

        start_time = time.time()
        self._log(f"开始处理 {len(images)} 张图片")
        
        # 创建临时目录用于存储下载的图片
        with tempfile.TemporaryDirectory() as temp_dir:
            self._log(f"创建临时目录: {temp_dir}")
            
            # 设置并发限制和超时
            semaphore = asyncio.Semaphore(2)  # 限制为最多同时处理 2 张图片
            timeout = aiohttp.ClientTimeout(total=60)  # 设置60秒总超时
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async def process_with_semaphore(image_url: str, alt: str) -> Tuple[str, str]:
                    async with semaphore:
                        try:
                            return await self._process_single_image(session, image_url, alt)
                        except Exception as e:
                            self._log(f"处理图片失败: {str(e)}")
                            return image_url, image_url  # 失败时返回原始URL
                
                # 创建所有任务
                tasks = [
                    asyncio.create_task(process_with_semaphore(image_url, alt))
                    for image_url, alt in images
                ]
                
                try:
                    # 等待所有任务完成，设置总超时
                    results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=120)
                except asyncio.TimeoutError:
                    self._log("图片处理总时间超过120秒，终止处理")
                    # 取消所有未完成的任务
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    # 获取已完成的结果
                    results = [(image_url, image_url) for image_url, _ in images]
                
                # 构建 URL 映射
                url_mapping = {old_url: new_url for old_url, new_url in results}
                
                # 保存 URL 映射到调试文件
                self._save_debug_file(
                    "debug_url_mapping.json",
                    json.dumps(url_mapping, ensure_ascii=False, indent=2)
                )
                
                # 打印处理结果
                elapsed = time.time() - start_time
                self._log(f"\n图片处理完成，共 {len(url_mapping)} 张图片，总耗时: {elapsed:.2f}秒")
                self._log("\nURL 映射关系:")
                for old_url, new_url in url_mapping.items():
                    self._log(f"{old_url} -> {new_url}")
                
                return url_mapping

    def replace_image_urls(self, markdown: str, url_mapping: Dict[str, str]) -> str:
        """替换 Markdown 中的图片 URL"""
        start_time = time.time()
        self._log("开始替换图片 URL")
        
        # 保存替换前的 Markdown
        self._save_debug_file("debug_before_replace.md", markdown)
        
        # 替换图片 URL
        for old_url, new_url in url_mapping.items():
            # 处理不同的图片格式
            patterns = [
                (f'!\\[([^\\]]*)\\]\\({re.escape(old_url)}\\)', f'![\\1]({new_url})'),  # 带 alt 的图片
                (f'!\\[\\]\\({re.escape(old_url)}\\)', f'![]({new_url})'),  # 无 alt 的图片
                (re.escape(old_url), new_url)  # 直接 URL
            ]
            
            for pattern, replacement in patterns:
                markdown = re.sub(pattern, replacement, markdown)
                
            self._log(f"替换图片 URL: {old_url} -> {new_url}")
        
        # 保存替换后的 Markdown
        self._save_debug_file("debug_final.md", markdown)
        
        elapsed = time.time() - start_time
        self._log(f"URL 替换完成，耗时: {elapsed:.2f}秒")
        
        return markdown

# 创建全局上传器实例
image_uploader = ImageUploader() 
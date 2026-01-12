"""
外部 LLM 处理服务模块

该模块负责调用外部 LLM API 对剪藏的文章进行智能处理，
生成分类、摘要、金句等结构化信息。
"""

import aiohttp
import asyncio
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from ..config import config
from ..services.notification import notifier
from ..logger import logger


@dataclass
class ScoringResult:
    """评分结果"""
    total_score: int = 0
    plus_items: List[str] = field(default_factory=list)
    minus_items: List[str] = field(default_factory=list)


@dataclass
class EntitiesResult:
    """实体识别结果"""
    company_worldwide: List[str] = field(default_factory=list)
    company_domestic: List[str] = field(default_factory=list)
    vip_worldwide: List[str] = field(default_factory=list)
    vip_domestic: List[str] = field(default_factory=list)
    industry_upper: List[str] = field(default_factory=list)
    industry_mid: List[str] = field(default_factory=list)
    industry_lower: List[str] = field(default_factory=list)


@dataclass
class LLMResult:
    """LLM 处理结果"""
    success: bool = False
    category: str = ""
    scoring: ScoringResult = field(default_factory=ScoringResult)
    entities: EntitiesResult = field(default_factory=EntitiesResult)
    new_title: str = ""
    paragraphs: List[str] = field(default_factory=list)
    hidden_info: List[str] = field(default_factory=list)
    golden_sentences: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    error: Optional[str] = None

    def to_yaml_dict(self) -> Dict[str, Any]:
        """转换为 YAML front matter 字典格式

        Returns:
            Dict: 用于 YAML front matter 的字典，使用原始字段名
        """
        return {
            "category": self.category,
            "new_title": self.new_title,
            "score": self.scoring.total_score,
            "score_plus": self.scoring.plus_items,
            "score_minus": self.scoring.minus_items,
            "entities_company_worldwide": self.entities.company_worldwide,
            "entities_company_domestic": self.entities.company_domestic,
            "entities_vip_worldwide": self.entities.vip_worldwide,
            "entities_vip_domestic": self.entities.vip_domestic,
            "entities_industry_upper": self.entities.industry_upper,
            "entities_industry_mid": self.entities.industry_mid,
            "entities_industry_lower": self.entities.industry_lower,
            "paragraphs": self.paragraphs,
            "hidden_info": self.hidden_info,
            "golden_sentences": self.golden_sentences,
            "processing_time": self.processing_time,
        }


class LLMService:
    """外部 LLM 处理服务

    负责调用外部 LLM API 对文章进行智能处理，支持：
    - 文章分类
    - 内容评分
    - 实体识别
    - 段落摘要
    - 金句提取
    """

    def __init__(self):
        """初始化 LLM 服务"""
        self._reload_config()

    def _reload_config(self):
        """重新加载配置"""
        self.enabled = config.get('llm.enabled', True)
        self.api_url = config.get('llm.url', '')
        self.api_key = config.get('llm.api_key', '')
        self.timeout = config.get('llm.timeout', 300)
        self.retry_count = config.get('llm.retry_count', 2)
        self.retry_delay = config.get('llm.retry_delay', 2)
        self.language = config.get('llm.language', 'auto')

    def is_enabled(self) -> bool:
        """检查 LLM 服务是否启用

        Returns:
            bool: 是否启用
        """
        self._reload_config()
        return self.enabled and bool(self.api_url)

    async def process(self, title: str, content: str) -> Optional[LLMResult]:
        """调用外部 LLM API 处理文章

        Args:
            title: 文章标题
            content: 文章 Markdown 内容

        Returns:
            LLMResult: 处理结果，失败返回 None
        """
        self._reload_config()

        if not self.is_enabled():
            logger.warning("[LLM] 服务未启用或未配置 URL")
            return None

        start_time = time.time()
        logger.info(f"[LLM] 开始处理文章: {title[:50]}...")

        # 构建请求数据
        request_data = {
            "title": title,
            "content": content,
            "language": self.language
        }

        # 重试逻辑
        last_error = None
        for attempt in range(self.retry_count + 1):
            try:
                result = await self._call_api(request_data)
                elapsed = time.time() - start_time
                logger.info(f"[LLM] 处理完成: category='{result.category}', score={result.scoring.total_score}, time={elapsed:.2f}s")
                return result

            except asyncio.TimeoutError:
                last_error = f"请求超时（{self.timeout}秒）"
                logger.warning(f"[LLM] 请求超时，第 {attempt + 1} 次尝试失败")

            except Exception as e:
                last_error = str(e)
                logger.warning(f"[LLM] 请求失败: {last_error}，第 {attempt + 1} 次尝试失败")

            # 如果不是最后一次尝试，等待后重试
            if attempt < self.retry_count:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.info(f"[LLM] 等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)

        # 所有重试都失败
        logger.error(f"[LLM] 处理失败，已重试 {self.retry_count} 次: {last_error}")
        notifier.send_progress("LLM 处理", f"⚠️ 处理失败: {last_error}")
        return None

    async def _call_api(self, request_data: Dict[str, Any]) -> LLMResult:
        """调用 LLM API

        Args:
            request_data: 请求数据

        Returns:
            LLMResult: 解析后的结果

        Raises:
            Exception: API 调用失败时抛出异常
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # 添加 API Key 鉴权
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        logger.debug(f"[LLM] 调用 API: {self.api_url}")

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                self.api_url,
                json=request_data,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API 返回错误状态码 {response.status}: {error_text[:200]}")

                result_data = await response.json()
                logger.debug(f"[LLM] API 响应成功: success={result_data.get('success')}")

                return self._parse_response(result_data)

    def _parse_response(self, data: Dict[str, Any]) -> LLMResult:
        """解析 API 响应数据

        Args:
            data: API 响应的 JSON 数据

        Returns:
            LLMResult: 解析后的结果对象
        """
        # 解析 scoring
        scoring_data = data.get('scoring', {})
        scoring = ScoringResult(
            total_score=scoring_data.get('total_score', 0),
            plus_items=scoring_data.get('plus_items', []),
            minus_items=scoring_data.get('minus_items', [])
        )

        # 解析 entities
        entities_data = data.get('entities', {})
        entities = EntitiesResult(
            company_worldwide=entities_data.get('company_worldwide', []),
            company_domestic=entities_data.get('company_domestic', []),
            vip_worldwide=entities_data.get('vip_worldwide', []),
            vip_domestic=entities_data.get('vip_domestic', []),
            industry_upper=entities_data.get('industry_upper', []),
            industry_mid=entities_data.get('industry_mid', []),
            industry_lower=entities_data.get('industry_lower', [])
        )

        # 构建完整结果
        return LLMResult(
            success=data.get('success', False),
            category=data.get('category', ''),
            scoring=scoring,
            entities=entities,
            new_title=data.get('new_title', ''),
            paragraphs=data.get('paragraphs', []),
            hidden_info=data.get('hidden_info', []),
            golden_sentences=data.get('golden_sentences', []),
            processing_time=data.get('processing_time', 0.0),
            error=data.get('error')
        )


# 创建全局服务实例
llm_service = LLMService()

"""
企业微信通知测试脚本

测试剪藏成功通知的展示效果。
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.notification import notifier
from app.services.llm_service import LLMResult, ScoringResult, EntitiesResult


def test_clip_success_notification():
    """测试剪藏成功通知（包含 LLM 结果）"""

    # 构造模拟的 LLM 结果
    llm_result = LLMResult(
        success=True,
        category="科技/人工智能",
        new_title="AI行业2025年发展趋势深度分析",
        scoring=ScoringResult(
            total_score=85,
            plus_items=["内容深度好", "数据详实", "观点独到"],
            minus_items=["部分论述逻辑跳跃", "缺少案例支撑"]
        ),
        paragraphs=[
            "AI 大模型进入商业化落地阶段",
            "算力需求持续增长，云厂商竞争加剧",
            "多模态成为下一个技术突破点"
        ],
        hidden_info=[
            "文中暗示某头部企业即将发布新产品",
            "作者与某投资机构有潜在利益关联"
        ],
        processing_time=12.3
    )

    # 发送测试通知
    notifier.send_clip_success(
        title="2025年AI行业深度报告",
        url="https://example.com/article",
        doc_path="Clippings/2025-01-14_AI行业报告.md",
        llm_result=llm_result
    )

    print("测试通知已提交，等待发送完成...")

    # 等待异步发送完成
    import time
    time.sleep(3)

    print("测试通知已发送，请检查企业微信群")


if __name__ == "__main__":
    test_clip_success_notification()

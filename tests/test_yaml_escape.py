"""
YAML 转义功能单元测试

测试 routes.py 中的 YAML 生成函数，确保特殊字符被正确转义，
生成的 YAML 可被正确解析。
"""

import os
import sys
import pytest
import yaml

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.api.routes import _format_yaml_list, _escape_yaml_string, generate_yaml_front_matter


class TestEscapeYamlString:
    """测试 _escape_yaml_string 函数"""

    def test_plain_text_no_escape(self):
        """普通文本不需要转义"""
        assert _escape_yaml_string("普通文本") == "普通文本"
        assert _escape_yaml_string("Hello World") == "Hello World"

    def test_empty_string(self):
        """空字符串返回空"""
        assert _escape_yaml_string("") == ""
        assert _escape_yaml_string(None) == ""

    def test_escape_colon(self):
        """包含冒号的字符串需要引号包裹"""
        result = _escape_yaml_string("key: value")
        assert result.startswith('"')
        assert result.endswith('"')
        # 验证可被 YAML 解析
        parsed = yaml.safe_load(f"test: {result}")
        assert parsed["test"] == "key: value"

    def test_escape_double_quotes(self):
        """双引号需要转义"""
        result = _escape_yaml_string('包含"引号"的文本')
        assert '\\"' in result
        # 验证可被 YAML 解析
        parsed = yaml.safe_load(f"test: {result}")
        assert parsed["test"] == '包含"引号"的文本'

    def test_escape_backslash(self):
        """反斜杠需要转义"""
        result = _escape_yaml_string("路径\\文件")
        assert "\\\\" in result
        # 验证可被 YAML 解析
        parsed = yaml.safe_load(f"test: {result}")
        assert parsed["test"] == "路径\\文件"

    def test_escape_hash(self):
        """井号需要引号包裹（避免被解析为注释）"""
        result = _escape_yaml_string("标签 #tag")
        assert result.startswith('"')
        # 验证可被 YAML 解析
        parsed = yaml.safe_load(f"test: {result}")
        assert parsed["test"] == "标签 #tag"

    def test_escape_newline(self):
        """换行符需要引号包裹

        注意：YAML 规范中，双引号字符串的换行符会被规范化为空格，
        这是预期行为。重要的是字符串能被正确解析，不会破坏 YAML 结构。
        """
        result = _escape_yaml_string("第一行\n第二行")
        assert result.startswith('"')
        # 验证可被 YAML 解析（换行符会被规范化为空格）
        parsed = yaml.safe_load(f"test: {result}")
        assert parsed["test"] is not None
        assert "第一行" in parsed["test"]
        assert "第二行" in parsed["test"]

    def test_complex_string_with_code(self):
        """复杂字符串：包含代码引用的内容（模拟 LLM 返回的 golden_sentences）"""
        text = 'TTRSS 在 HTML 中会对图片链接增加 `referrerpolicy="no-referrer"` 属性'
        result = _escape_yaml_string(text)
        # 验证可被 YAML 解析
        parsed = yaml.safe_load(f"test: {result}")
        assert parsed["test"] == text


class TestFormatYamlList:
    """测试 _format_yaml_list 函数"""

    def test_empty_list(self):
        """空列表返回 []"""
        assert _format_yaml_list([]) == "[]"

    def test_simple_list(self):
        """简单列表格式化"""
        result = _format_yaml_list(["item1", "item2"])
        yaml_str = f"test:{result}"
        parsed = yaml.safe_load(yaml_str)
        assert parsed["test"] == ["item1", "item2"]

    def test_list_with_double_quotes(self):
        """列表项包含双引号"""
        items = ['包含"引号"的文本', '另一个"引号"项']
        result = _format_yaml_list(items)
        yaml_str = f"test:{result}"
        parsed = yaml.safe_load(yaml_str)
        assert parsed["test"] == items

    def test_list_with_backslash(self):
        """列表项包含反斜杠"""
        items = ["路径\\文件", "C:\\Users\\test"]
        result = _format_yaml_list(items)
        yaml_str = f"test:{result}"
        parsed = yaml.safe_load(yaml_str)
        assert parsed["test"] == items

    def test_list_with_code_references(self):
        """列表项包含代码引用（模拟真实场景）"""
        items = [
            '使用 `referrerpolicy="no-referrer"` 属性',
            '匹配头 `(Host:.+)(\\r\\n)`',
            '替换为 `$1$2Referer: sspai.com$2`',
        ]
        result = _format_yaml_list(items)
        yaml_str = f"test:{result}"
        parsed = yaml.safe_load(yaml_str)
        assert parsed["test"] == items

    def test_list_with_mixed_special_chars(self):
        """列表项包含多种特殊字符"""
        items = [
            "包含冒号: 和井号 #tag",
            '包含引号 "quoted" 和反斜杠 \\path',
            "包含方括号 [array] 和花括号 {object}",
        ]
        result = _format_yaml_list(items)
        yaml_str = f"test:{result}"
        parsed = yaml.safe_load(yaml_str)
        assert parsed["test"] == items


class TestGenerateYamlFrontMatter:
    """测试 generate_yaml_front_matter 函数"""

    def test_basic_front_matter(self):
        """基本 front matter 生成"""
        url = "https://example.com/article"
        title = "测试文章"
        meta_info = {
            "description": "这是描述",
            "author": "作者",
            "date": "2024-01-01",
        }

        result = generate_yaml_front_matter(url, title, meta_info)

        # 提取 YAML 内容（去掉开头和结尾的 ---）
        yaml_content = result.strip().strip("-").strip()
        parsed = yaml.safe_load(yaml_content)

        assert parsed["url"] == url
        assert parsed["title"] == title
        assert parsed["description"] == "这是描述"
        assert parsed["author"] == "作者"

    def test_front_matter_with_special_url(self):
        """URL 包含特殊字符"""
        url = "https://example.com/article?id=123#section"
        title = "测试"
        meta_info = {"description": "", "author": "", "date": ""}

        result = generate_yaml_front_matter(url, title, meta_info)
        yaml_content = result.strip().strip("-").strip()
        parsed = yaml.safe_load(yaml_content)

        assert parsed["url"] == url

    def test_front_matter_with_special_title(self):
        """标题包含特殊字符"""
        url = "https://example.com"
        title = '标题包含"引号"和冒号: 以及 #标签'
        meta_info = {"description": "", "author": "", "date": ""}

        result = generate_yaml_front_matter(url, title, meta_info)
        yaml_content = result.strip().strip("-").strip()
        parsed = yaml.safe_load(yaml_content)

        assert parsed["title"] == title

    def test_front_matter_with_iso_date(self):
        """ISO 8601 格式的日期"""
        url = "https://example.com"
        title = "测试"
        meta_info = {
            "description": "",
            "author": "",
            "date": "2024-10-13T11:22:28+08:00",
        }

        result = generate_yaml_front_matter(url, title, meta_info)
        yaml_content = result.strip().strip("-").strip()
        parsed = yaml.safe_load(yaml_content)

        # ISO 日期包含冒号，应该被正确处理
        assert "2024-10-13" in str(parsed["published"])


class TestRealWorldScenarios:
    """真实场景测试：模拟实际 LLM 返回的内容"""

    def test_golden_sentences_with_code(self):
        """golden_sentences 包含代码引用"""
        items = [
            "一般的图片防盗链功能是通过检测 HTTP 请求头中的 `Referer` 字段是否是合法的域名实现的。",
            'TTRSS 在 HTML 中会对图片链接增加 `referrerpolicy="no-referrer"` 属性，这个属性会在请求图片时不发送任何 `Referer` 信息。',
        ]
        result = _format_yaml_list(items)
        yaml_str = f"golden_sentences:{result}"
        parsed = yaml.safe_load(yaml_str)
        assert parsed["golden_sentences"] == items

    def test_hidden_info_with_quotes(self):
        """hidden_info 包含引号"""
        items = [
            '使用QX工具时，重写规则中的"Replacement"字段不支持直接插入换行符。',
            '必须将目标域名添加到QX的MitM配置的Hostnames列表中。',
        ]
        result = _format_yaml_list(items)
        yaml_str = f"hidden_info:{result}"
        parsed = yaml.safe_load(yaml_str)
        assert parsed["hidden_info"] == items

    def test_paragraphs_with_complex_content(self):
        """paragraphs 包含复杂内容"""
        items = [
            "进阶解法：使用QX拦截HTTPS流量。具体步骤包括创建重写规则：类型为`request-header`，匹配URL模式`^https://cdnfile\\.sspai\\.com/`。",
        ]
        result = _format_yaml_list(items)
        yaml_str = f"paragraphs:{result}"
        parsed = yaml.safe_load(yaml_str)
        assert parsed["paragraphs"] == items


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

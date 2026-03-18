# URL 爬取技术参考文档

> 本文档基于 `obsidian-clip-api-couchdb` 项目的实际实现，系统梳理了 URL 内容爬取的完整技术方案，可作为搭建独立 URL 爬取服务的开发参考。

---

## 1. 整体架构概览

```
┌─────────────┐
│  POST /clip │  接收 URL
└──────┬──────┘
       ▼
┌──────────────┐
│  WebParser   │  HTTP 请求 + 元数据提取
│  (requests)  │
└──────┬───────┘
       ▼
┌────────────────────┐
│ MarkdownConverter  │  HTML 清理 + 图片提取 + Markdown 转换
│ (bs4 + markdownify)│
└──────┬─────────────┘
       ▼
┌──────────────────────────────────┐
│  并行异步处理 (asyncio.gather)    │
│  ├─ ImageUploader (aiohttp)     │  图片下载 → 上传图床
│  └─ LLMService    (aiohttp)     │  调用 LLM API
└──────────────────────────────────┘
       ▼
┌──────────────┐
│  存储 / 输出  │  YAML front matter + Markdown 正文
└──────────────┘
```

### 处理流程时序

| 步骤 | 模块 | 同步/异步 | 说明 |
|------|------|----------|------|
| 1 | `WebParser.parse_url()` | 同步 | HTTP 请求获取原始 HTML |
| 2 | `MarkdownConverter.convert()` | 同步 | HTML → Markdown + 图片列表 |
| 3a | `ImageUploader.upload_images()` | 异步 | 并发下载+上传图片 |
| 3b | `LLMService.process()` | 异步 | 调用 LLM API（与 3a 并行） |
| 4 | `ImageUploader.replace_image_urls()` | 同步 | 替换 Markdown 中的图片地址 |
| 5 | `generate_yaml_front_matter()` | 同步 | 组装最终输出 |

---

## 2. 依赖库清单

| 库名 | 版本要求 | 职责 | 是否必须 |
|------|---------|------|---------|
| `requests` | >= 2.31.0 | 同步 HTTP 请求，获取网页 HTML | 是 |
| `beautifulsoup4` | >= 4.12.3 | HTML 解析（标题/元数据/图片提取、标签清理） | 是 |
| `markdownify` | >= 0.11.6 | HTML → Markdown 转换 | 是 |
| `aiohttp` | >= 3.9.3 | 异步 HTTP（图片下载/上传、LLM 调用） | 是 |
| `certifi` | >= 2025.0.0 | SSL 证书验证 | 是 |
| `re` (标准库) | - | 正则表达式，微信内容提取等 | 是 |

---

## 3. 模块详解

### 3.1 WebParser — 网页获取与元数据提取

**源文件**: `app/services/web_parser.py`

#### 3.1.1 HTTP 请求策略

```python
class WebParser:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36'
        }

    def parse_url(self, url: str) -> tuple:
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        html = response.text
```

**关键设计决策**:
- 使用 `requests` 同步库（而非 `aiohttp`），因为网页获取是流程的第一步，必须阻塞等待
- 超时 30 秒，适合大多数网页
- 伪装 Chrome UA，避免被反爬拦截
- 通过 `raise_for_status()` 快速失败

**新项目建议**:
- 考虑增加重试机制（当前实现未做重试）
- 考虑增加代理支持（反爬场景）
- 考虑使用 `httpx` 替代 `requests`，统一同步/异步接口
- 考虑增加 `Accept-Language`、`Referer` 等请求头以提高兼容性
- 对于 JS 渲染的页面，考虑集成 Playwright/Selenium

#### 3.1.2 HTML 预清理

```python
def _clean_html(self, html: str) -> str:
    """将 data-src 替换为 src（处理懒加载）"""
    html = re.sub(r'data-src="([^"]*)"', r'src="\1"', html)
    return html
```

**适用场景**: 微信公众号等使用懒加载的页面，图片 URL 存储在 `data-src` 而非 `src` 属性中。

#### 3.1.3 标题提取策略（优先级递降）

```python
def _extract_title(self, soup: BeautifulSoup) -> str:
    # 优先级 1: OpenGraph 标签
    meta_title = soup.find('meta', property='og:title')

    # 优先级 2: <title> 标签
    title_tag = soup.find('title')

    # 优先级 3: <h1> 标签
    h1_tag = soup.find('h1')

    # 兜底: 返回空字符串（由调用方处理）
    return ""
```

**设计理由**:
- `og:title` 通常是最干净的标题（无站点后缀）
- `<title>` 标签可能包含 ` - 站点名` 后缀
- `<h1>` 是最后的兜底

**新项目建议**:
- 增加 `<title>` 标签清理（去除 ` - 站点名`、` | 站点名` 后缀）
- 增加 `twitter:title` 的支持
- 增加标题长度限制和特殊字符过滤

#### 3.1.4 元数据提取

```python
def _extract_meta_info(self, html: str) -> dict:
    meta_info = {
        'author': '',
        'date': '',
        'description': ''
    }
```

**提取规则汇总**:

| 字段 | 尝试的 meta 标签（按优先级） | 备注 |
|------|---------------------------|------|
| author | `name="author"` → `property="og:article:author"` → `property="article:author"` → `name="twitter:creator"` | |
| date | `name="article:published_time"` → `property="article:published_time"` → `name="publishedDate"` → `name="date"` | 兜底使用正则匹配页面文本 |
| description | `name="description"` → `property="og:description"` → `name="twitter:description"` | |

**日期兜底正则**:
```python
date_patterns = [
    r'\d{4}-\d{2}-\d{2}',      # 2024-01-15
    r'\d{4}/\d{2}/\d{2}',      # 2024/01/15
    r'\d{4}年\d{2}月\d{2}日'    # 2024年01月15日
]
```

**微信公众号特殊处理**:
```python
if 'mp.weixin.qq.com' in html:
    publish_time_match = re.search(r'var publish_time = "([^"]+)"', html)
```

---

### 3.2 MarkdownConverter — HTML 清理与格式转换

**源文件**: `app/services/markdown_converter.py`

#### 3.2.1 图片提取（两条路径）

**路径 A: 标准 `<img>` 标签提取**

```python
def _extract_images(self, html: str) -> List[Tuple[str, str]]:
    soup = BeautifulSoup(html, 'html.parser')
    for img in soup.find_all('img'):
        src = img.get('src', '') or img.get('data-src', '')
        if src:
            alt = img.get('alt', '')
            images.append((src, alt))
    return images  # List[(url, alt_text)]
```

**路径 B: 微信 JS 变量提取**

微信公众号正文图片不在 `<img>` 标签中，而是存储在 JS 变量 `picture_page_info_list` 中：

```python
def _extract_wechat_images(self, html: str) -> List[Tuple[str, str]]:
    # 匹配 JS 变量
    pattern = r"picture_page_info_list\s*=\s*(\[[\s\S]*?\])\s*\.slice"
    match = re.search(pattern, html)

    # 提取每个图片对象的第一个 cdn_url（主图）
    object_pattern = r"\{\s*width:[^}]*?cdn_url:\s*'([^']+)'"
    main_urls = re.findall(object_pattern, raw_list)

    # 解码转义字符
    url = url.replace('\\x26amp;', '&')
    url = url.replace('\\x26', '&')
```

**图片合并策略**: 微信 JS 图片优先，HTML `<img>` 标签图片次之，通过 URL 去重。

#### 3.2.2 微信公众号内容提取（三级降级策略）

```python
def _clean_wechat_content(self, html: str) -> str:
    # 方式 1（优先）: 截断方式 — 查找"预览时标签不可点"的位置截断
    cut_point = html.find("预览时标签不可点")
    if cut_point != -1:
        return html[:cut_point].strip()

    # 方式 2（降级）: 从 JS 变量 content_noencode 提取
    js_content = self._extract_wechat_js_content(html)
    if js_content:
        # 解码: \x0a→\n, \x3c→<, \x3e→>, \x22→" 等
        return result

    # 方式 3（兜底）: 使用原始 HTML
    return html
```

**JS 内容解码映射表**:

| 转义序列 | 解码结果 | 说明 |
|---------|---------|------|
| `\x0a` | `\n` | 换行符 |
| `\x3c` | `<` | HTML 左尖括号 |
| `\x3e` | `>` | HTML 右尖括号 |
| `\x22` | `"` | 双引号 |
| `\x26amp;` | `&` | & 符号 |
| `\x27` | `'` | 单引号 |
| `\/` | `/` | 斜杠 |
| `\\` | `\` | 反斜杠 |

#### 3.2.3 HTML 清理规则

```python
def _clean_html(self, html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')

    # 1. 移除无关标签
    for tag in soup(['script', 'style', 'meta', 'link', 'noscript', 'iframe']):
        tag.decompose()

    # 2. 移除空 <span> 标签
    for span in soup.find_all('span'):
        if not span.get_text(strip=True):
            span.decompose()

    # 3. 处理链接: 移除 javascript: 链接，只保留文本
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if not href or 'javascript:' in href:
            if text:
                a.replace_with(text)
            else:
                a.decompose()

    # 4. 处理 <section> 标签: 含链接/标题/图片时保留结构，否则提取纯文本
    # 5. 确保标题前后有换行
```

#### 3.2.4 markdownify 转换配置

```python
markdown = md(html,
    heading_style="ATX",           # 使用 # 样式标题
    bullets="-",                   # 使用 - 作为列表标记
    autolinks=True,                # 自动转换链接
    wrap=False,                    # 不自动换行（保持原文格式）
    default_title=True,
    escape_underscores=True,       # 转义 _（避免误判为斜体）
    newline_style="\n",
    strip=['script', 'style', 'meta', 'link', 'noscript', 'iframe'],
    options={
        'emphasis_mark': '*',      # *斜体*
        'strong_mark': '**',       # **加粗**
        'code_mark': '`',          # `代码`
        'hr_mark': '---',          # 分隔线
        'br_mark': '  \n',         # 软换行（两空格+换行）
        'link_brackets': True,
        'convert_links': True,
        'keep_links': True,
    }
)
```

#### 3.2.5 Markdown 后处理

```python
# 压缩连续空行（最多保留 2 个换行）
markdown = re.sub(r'\n{3,}', '\n\n', markdown)

# 确保链接后有双换行
markdown = re.sub(r'(\[.*?\]\(.*?\))\n', r'\1\n\n', markdown)

# 微信 JS 模式下正文无图片时，在开头插入图片
if wechat_images and '![' not in markdown:
    image_section = '\n\n'.join(
        [f'![图片{i+1}]({url})' for i, (url, _) in enumerate(wechat_images)]
    )
    markdown = image_section + '\n\n' + markdown
```

---

### 3.3 ImageUploader — 异步图片处理

**源文件**: `app/services/image_uploader.py`

#### 3.3.1 异步下载图片

```python
async def _download_image(self, session: aiohttp.ClientSession, image_url: str) -> bytes:
    async with session.get(image_url) as response:
        if response.status != 200:
            raise Exception(f"下载失败，状态码: {response.status}")
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise Exception(f"非图片类型: {content_type}")
        return await response.read()
```

#### 3.3.2 上传到图床（PicGo）

```python
async def _upload_to_picgo(self, session, image_data: bytes, filename: str) -> str:
    form = aiohttp.FormData()
    form.add_field('image', image_data, filename=filename, content_type='image/jpeg')
    upload_url = urljoin(self.picgo_server, self.upload_path)

    # 最多重试 3 次，每次间隔 2 秒
    max_retries = 3
    # ... 重试逻辑 ...
```

#### 3.3.3 并发控制策略

```python
async def upload_images(self, images):
    semaphore = asyncio.Semaphore(2)          # 最多 2 张并发
    timeout = aiohttp.ClientTimeout(total=60) # 单任务 60 秒超时

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [process_with_semaphore(url, alt) for url, alt in images]
        results = await asyncio.wait_for(
            asyncio.gather(*tasks), timeout=120  # 总超时 120 秒
        )
```

**超时控制层次**:

| 层级 | 超时时间 | 说明 |
|------|---------|------|
| 单次 PicGo 上传 | 30s | 单个 HTTP 请求超时 |
| 单任务 aiohttp session | 60s | 包含下载+上传的总时间 |
| 全部图片处理 | 120s | `asyncio.wait_for` 的总超时 |

#### 3.3.4 URL 替换

```python
def replace_image_urls(self, markdown: str, url_mapping: Dict[str, str]) -> str:
    for old_url, new_url in url_mapping.items():
        old_url_escaped = re.escape(old_url)
        # 替换 ![alt](url) 格式
        markdown = re.sub(f'!\\[(.*?)\\]\\({old_url_escaped}\\)',
                         f'![\\1]({new_url})', markdown)
        # 兜底：直接替换裸 URL
        markdown = markdown.replace(old_url, new_url)
    return markdown
```

---

## 4. 错误处理与容错机制

### 4.1 网页获取失败

```python
# web_parser.py
except requests.RequestException as e:
    error_msg = f"获取网页内容失败: {str(e)}"
    raise Exception(error_msg)  # 向上抛出，终止整个剪藏流程
```

**设计理由**: 网页获取是核心步骤，失败则无法继续。

### 4.2 图片处理失败

```python
# image_uploader.py - 单张图片失败不影响其他图片
except Exception as e:
    return image_url, image_url  # 失败时返回原始 URL

# routes.py - 图片上传整体失败不影响文章保存
if isinstance(result, Exception):
    continue  # 跳过，使用原始图片 URL
```

### 4.3 LLM 处理失败

```python
# routes.py - LLM 失败不影响文章保存
if isinstance(result, Exception):
    continue  # 文章照常保存，只是不包含 LLM 字段
```

**容错原则**: 只有网页获取失败会终止流程，图片和 LLM 处理失败都采用优雅降级。

---

## 5. 调试支持

项目通过 `debug_manager` 保存每个阶段的中间产物：

| 文件 | 前缀 | 内容 |
|------|------|------|
| `original.html` | `web` | 原始 HTTP 响应 |
| `cleaned.html` | `web` | data-src 替换后的 HTML |
| `original.html` | `md` | 进入 Markdown 转换器的 HTML |
| `images.txt` | `md` | 提取的图片 URL 列表 |
| `processed.html` | `md` | 清理后待转换的 HTML |
| `result.md` | `md` | 转换后的 Markdown |
| `before_replace.md` | `img` | URL 替换前的 Markdown |
| `url_mapping.json` | `img` | 图片 URL 新旧映射 |
| `final.md` | `img` | 最终 Markdown |

**新项目建议**: 保留此调试机制，对排查爬取问题非常有帮助。

---

## 6. 新项目开发建议

### 6.1 推荐技术选型

| 需求 | 本项目方案 | 推荐升级方案 | 理由 |
|------|-----------|-------------|------|
| HTTP 请求 | `requests` (同步) | `httpx` (同步+异步) | 统一接口，内置重试、HTTP/2 支持 |
| HTML 解析 | `beautifulsoup4` | `beautifulsoup4` (保持) | 成熟稳定，够用 |
| 正文提取 | 手动清理 | `readability-lxml` 或 `trafilatura` | 自动识别正文区域，减少手动规则 |
| HTML→Markdown | `markdownify` | `markdownify` (保持) | 转换质量好，可配置性强 |
| 异步 HTTP | `aiohttp` | `httpx` (异步模式) | 与同步请求统一库 |
| JS 渲染 | 不支持 | `playwright` | SPA 页面爬取 |

### 6.2 建议的服务架构

```
┌──────────────────────────────────────────────────┐
│              URL 爬取服务 API                     │
│              (FastAPI)                           │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────┐ │
│  │ Fetcher     │  │ Parser       │  │ Output  │ │
│  │             │  │              │  │         │ │
│  │ - 普通 HTTP │  │ - 标题提取   │  │ - JSON  │ │
│  │ - 带渲染    │  │ - 元数据提取 │  │ - MD    │ │
│  │ - 代理支持  │  │ - 正文提取   │  │ - HTML  │ │
│  │ - 重试/限流 │  │ - 图片提取   │  │         │ │
│  └─────────────┘  │ - 微信适配   │  └─────────┘ │
│                   │ - HTML→MD    │               │
│                   └──────────────┘               │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ 站点适配器注册表 (Site Adapters)            │  │
│  │                                            │  │
│  │ - WeChat  : 微信公众号                      │  │
│  │ - Zhihu   : 知乎                           │  │
│  │ - Default : 通用适配器                      │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### 6.3 站点适配器模式

本项目中微信公众号的特殊处理逻辑散布在多个方法中。新项目建议采用 **站点适配器模式**：

```python
class SiteAdapter:
    """站点适配器基类"""

    @staticmethod
    def match(url: str) -> bool:
        """判断该适配器是否匹配给定 URL"""
        raise NotImplementedError

    def extract_title(self, soup: BeautifulSoup) -> str:
        """提取标题"""
        raise NotImplementedError

    def extract_content(self, html: str) -> str:
        """提取正文 HTML"""
        raise NotImplementedError

    def extract_images(self, html: str) -> List[Tuple[str, str]]:
        """提取图片列表"""
        raise NotImplementedError

    def extract_meta(self, html: str) -> dict:
        """提取元数据"""
        raise NotImplementedError


class WeChatAdapter(SiteAdapter):
    """微信公众号适配器"""

    @staticmethod
    def match(url: str) -> bool:
        return 'mp.weixin.qq.com' in url

    # ... 微信特有的提取逻辑 ...


class DefaultAdapter(SiteAdapter):
    """通用适配器"""
    # ... 通用提取逻辑 ...


# 适配器注册表
ADAPTERS = [WeChatAdapter(), ZhihuAdapter(), ...]

def get_adapter(url: str) -> SiteAdapter:
    for adapter in ADAPTERS:
        if adapter.match(url):
            return adapter
    return DefaultAdapter()
```

### 6.4 需要复用的核心逻辑

以下是本项目中经过验证、值得直接复用的逻辑：

1. **标题提取优先级**: `og:title` → `<title>` → `<h1>` → 默认值
2. **元数据提取规则**: 多种 meta 标签的探测顺序
3. **日期正则兜底**: 在页面文本中匹配日期格式
4. **微信全套处理**: 懒加载处理、JS 变量提取、图片提取、内容截断
5. **markdownify 配置参数**: 经过调优的转换参数组合
6. **图片并发控制**: Semaphore + 分层超时的模式
7. **URL 替换的正则方案**: 安全地替换 Markdown 中的图片 URL
8. **调试中间产物保存**: 每个阶段保存文件便于排查

---

## 7. 已知局限与改进方向

| 局限 | 现状 | 改进建议 |
|------|------|---------|
| 不支持 JS 渲染页面 | 仅获取静态 HTML | 集成 Playwright |
| 无请求重试 | 网页获取失败直接报错 | 增加指数退避重试 |
| 无代理支持 | 直连请求 | 增加代理池配置 |
| 无频率限制 | 无限制 | 增加请求限流（避免被封 IP） |
| 编码自动检测 | 依赖 requests 默认 | 增加 `chardet` / `charset-normalizer` 检测 |
| 微信逻辑耦合 | 硬编码在通用模块中 | 使用站点适配器模式解耦 |
| 无缓存机制 | 每次请求都重新抓取 | 增加 Redis/文件缓存 |
| User-Agent 固定 | 单一 Chrome UA | UA 池轮换 |

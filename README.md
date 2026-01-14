# Obsidian 剪藏 API

一个用于剪藏网页到 Obsidian 的 API 服务。项目基于 [obcsapi-go](https://github.com/kkbt0/obcsapi-go) 用 Python 重写。

## 功能特点

- 支持网页内容解析和 Markdown 转换
- 自动提取图片并上传到 PicGo 图床（支持多种图床服务）
- **外部 LLM 智能处理**：自动分类、摘要、金句提取等（默认开启）
- 保存到 CouchDB 数据库，支持 Obsidian 同步 ,需要使用[ obsidian-livesync 插件](https://github.com/vrtmrz/obsidian-livesync/blob/main/docs/setup_own_server.md)
- 企业微信通知（剪藏开始、成功、失败等状态）
- 支持 API 鉴权
- 支持 Docker 部署

## 快速开始

### 1. 部署 PicGo 服务

首先需要部署 PicGo 服务作为图床服务。推荐使用 [PicList](https://github.com/Kuingsmile/PicList) 的 Docker 版本：

```bash
docker run -d \
  --name piclist \
  --restart always \
  -p 36677:36677 \
  -v "./piclist:/root/.piclist" \
  kuingsmile/piclist:latest \
  node /usr/local/bin/picgo-server -k your-secret-key
```

### 2. 部署剪藏 API 服务

#### 使用 Docker 部署（推荐）

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/obsidian-clip-api-couchdb.git
cd obsidian-clip-api-couchdb
```

2. 创建配置文件：
```bash
cp config.yaml.example config.yaml
```

3. 编辑 `config.yaml`，配置必要的参数：
```yaml
# API 鉴权配置
api:
  enabled: true
  key: "your-secret-api-key"

# CouchDB 配置
couchdb:
  url: "http://username:password@your-couchdb-host:5984/"
  db_name: "your-db-name"

# PicGo 配置
picgo:
  enabled: true
  server: "http://localhost:36677"
  upload_path: "/upload?key=your-secret-key"  # 与 PicGo 服务配置的密钥一致

# 企业微信群机器人通知配置
work_wechat:
  enabled: true
  webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR-WEBHOOK-KEY"
  at_all: false

# 外部 LLM 处理配置（可选，默认开启）
llm:
  enabled: true
  url: "http://127.0.0.1:8080/api/v1/process"
  api_key: "your-llm-api-key"
  timeout: 180
```

4. 启动服务：
```bash
docker-compose up -d
```

#### 本地运行

1. 安装 uv（如果尚未安装）：
```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. 创建虚拟环境并安装依赖：
```bash
uv venv
uv pip install -e .
```

3. 配置 `config.yaml`（同上）

4. 运行服务：
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8901
```

## API 使用

### 剪藏文章

```bash
curl -X POST http://localhost:8901/api/clip \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key" \
  -d '{"url": "https://example.com/article"}'
```

响应示例：
```json
{
  "title": "文章标题",
  "doc_id": "20240306123456_article_title"
}
```

## 配置说明

### 图床配置

支持通过 PicGo 服务上传图片到多种图床：
- SM.MS
- GitHub
- Imgur
- 腾讯云 COS
- 阿里云 OSS
- 七牛云
- WebDAV
- 本地存储
- 等多种图床服务

### 外部 LLM 处理

启用后，剪藏的文章会自动调用外部 LLM API 进行智能处理，生成以下字段并存储到 Obsidian YAML 属性中：

| 字段 | 说明 |
|------|------|
| category | 文章分类 |
| new_title | AI 优化后的标题 |
| score | 文章评分 |
| score_plus / score_minus | 评分加分/减分项 |
| entities_* | 实体识别（公司、VIP、行业等） |
| paragraphs | 段落摘要 |
| hidden_info | 隐藏信息/深度洞察 |
| golden_sentences | 金句提取 |
| processing_time | 处理耗时 |

**配置项说明**：
- `enabled`: 是否启用，默认 `true`
- `url`: LLM API 完整地址
- `api_key`: API 鉴权密钥（通过 X-API-Key 请求头传递）
- `timeout`: 超时时间，默认 180 秒
- `retry_count`: 重试次数，默认 2 次
- `retry_delay`: 重试延迟，默认 2 秒

**容错机制**：LLM 处理失败不会影响文章保存，只是不包含 LLM 生成的字段。

### 企业微信通知

使用企业微信群机器人 Webhook 发送通知，需要先在企业微信群中添加群机器人并获取 Webhook 地址。

**配置项说明**：
- `enabled`: 是否启用通知，默认 `false`
- `webhook_url`: 群机器人 Webhook 地址
- `at_all`: 发送消息时是否 @所有人

**通知时机**：
- 开始剪藏时：显示时间、链接和图床状态
- 剪藏成功时：显示标题、链接、保存路径，以及 LLM 分析结果（Markdown 格式）
- 发生错误时：显示错误信息

**剪藏成功通知示例**（启用 LLM 时）：

```markdown
## ✅ 剪藏成功

**标题**: 2025年AI行业深度报告
**链接**: https://example.com/article
**路径**: Clippings/2025-01-14_AI行业报告.md

---

### 📊 AI 分析结果

**分类**: 科技/人工智能
**优化标题**: AI行业2025年发展趋势分析
**评分**: 85

### 📝 段落摘要
- AI 大模型进入商业化落地阶段
- 算力需求持续增长

### 🔍 隐藏信息
- 文中暗示某头部企业即将发布新产品

⏱️ AI 处理耗时: 12.3s
```

### 安全说明

- 配置文件包含敏感信息，请妥善保管
- 不要将包含真实配置的 `config.yaml` 提交到代码仓库
- 建议使用环境变量或密钥管理系统来管理敏感信息

## 许可证

MIT 

## 配置说明

服务使用 `config.yaml` 进行配置，该文件不会被包含在 Docker 镜像中。用户需要：

1. 创建自己的 `config.yaml` 文件
2. 通过 volume 挂载到容器中
3. 或通过环境变量覆盖配置

示例配置：
```yaml
api:
  enabled: true
  key: "your-secret-api-key"

couchdb:
  url: "your-couchdb-url"
  db_name: "your-db-name"

# ... 其他配置项
```

## 安全说明

- 配置文件包含敏感信息，请妥善保管
- 不要将包含真实配置的 `config.yaml` 提交到代码仓库
- 建议使用环境变量或密钥管理系统来管理敏感信息 
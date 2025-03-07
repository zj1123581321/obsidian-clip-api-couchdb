# Obsidian 剪藏 API

一个用于剪藏网页到 Obsidian 的 API 服务。项目基于 [obcsapi-go](https://github.com/kkbt0/obcsapi-go) 用 Python 重写。

## 功能特点

- 支持网页内容解析和 Markdown 转换
- 自动提取图片并上传到 PicGo 图床（支持多种图床服务）
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
  url: "http://your-couchdb-url:5984/"
  db_name: "your-db-name"

# PicGo 配置
picgo:
  enabled: true
  server: "http://localhost:36677"
  upload_path: "/upload?key=your-secret-key"  # 与 PicGo 服务配置的密钥一致

# 企业微信配置
work_wechat:
  corp_id: "your-corp-id"
  agent_id: "your-agent-id"
  corp_secret: "your-corp-secret"
  at_all: true
```

4. 启动服务：
```bash
docker-compose up -d
```

#### 本地运行

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置 `config.yaml`（同上）

3. 运行服务：
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8901
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

### 企业微信通知

服务会在以下情况发送通知：
- 开始剪藏时：显示时间、链接和图床状态
- 剪藏成功时：显示标题、链接和保存路径
- 发生错误时：显示错误信息

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
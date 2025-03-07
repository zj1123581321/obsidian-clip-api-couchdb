# Obsidian Clip API

一个用于剪藏网页到 Obsidian 的 API 服务。项目基于 https://github.com/kkbt0/obcsapi-go 用 python 重写。

## 功能特点

- 支持网页内容解析和 Markdown 转换
- 自动提取并上传图片到图床
- 保存到 CouchDB 数据库
- 企业微信通知
- 支持 Docker 部署

## 安装

### 本地运行

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/obsidian-clip-api-couchdb.git
cd obsidian-clip-api-couchdb
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置 `config.yaml`：
```yaml
name: obsidian-clip-api-couchdb
version: v1.0.0
description: 网页剪藏 API 服务

# 服务配置
host: 0.0.0.0
port: 8901

# CouchDB 配置
couchdb:
  url: http://admin:password@localhost:5984/
  db_name: obsidian

# 企业微信配置
work_wechat:
  corp_id: your_corp_id
  agent_id: your_agent_id
  corp_secret: your_corp_secret
  token: your_token
  encoding_aes_key: your_encoding_aes_key
  user_id: your_user_id
  at_all: true

# PicGo 配置
picgo:
  server: http://localhost:36677
  upload_path: /upload

# 调试模式
debug: true
```

4. 运行服务：
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8901
```

### Docker 部署

1. 构建镜像：
```bash
docker-compose build
```

2. 启动服务：
```bash
docker-compose up -d
```

## API 使用

### 剪藏文章

```bash
curl -X POST http://localhost:8901/api/clip \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

响应示例：
```json
{
  "title": "文章标题",
  "doc_id": "20240306123456_article_title"
}
```

## 开发

### 项目结构

```
obsidian-clip-api-couchdb/
├── app/
│   ├── api/
│   │   └── routes.py
│   ├── services/
│   │   ├── web_parser.py
│   │   ├── markdown_converter.py
│   │   ├── image_uploader.py
│   │   ├── couchdb_service.py
│   │   └── notification.py
│   ├── config.py
│   └── main.py
├── config.yaml
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### 添加新功能

1. 在 `app/services` 中添加新的服务模块
2. 在 `app/api/routes.py` 中添加新的路由
3. 更新 `config.yaml` 添加新的配置项

## 许可证

MIT 
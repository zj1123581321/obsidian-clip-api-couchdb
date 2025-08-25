# 安装指南

本指南将帮助您快速安装和配置 Obsidian 剪藏 API 服务。支持 Docker 部署（推荐）和本地安装两种方式。

## 系统要求

### 基础要求
- Python 3.11 或更高版本
- 64 位操作系统（Linux、Windows、macOS）
- 至少 512MB 可用内存
- 至少 1GB 可用磁盘空间

### 依赖服务
- **CouchDB**: 用于数据存储，需要支持 Obsidian LiveSync
- **PicGo Server** (可选): 用于图片上传到图床
- **企业微信应用** (可选): 用于消息推送

## Docker 部署（推荐）

Docker 部署是最简单和推荐的安装方式，可以避免环境配置问题。

### 1. 安装前置服务

#### 部署 PicGo 服务（可选）

如果需要图床功能，建议使用 PicList 的 Docker 版本：

```bash
docker run -d \
  --name piclist \
  --restart always \
  -p 36677:36677 \
  -v "./piclist:/root/.piclist" \
  kuingsmile/piclist:latest \
  node /usr/local/bin/picgo-server -k your-secret-key
```

#### 部署 CouchDB 服务

```bash
docker run -d \
  --name couchdb \
  --restart always \
  -p 5984:5984 \
  -e COUCHDB_USER=admin \
  -e COUCHDB_PASSWORD=your-password \
  -v couchdb-data:/opt/couchdb/data \
  couchdb:latest
```

### 2. 克隆项目

```bash
git clone https://github.com/yourusername/obsidian-clip-api-couchdb.git
cd obsidian-clip-api-couchdb
```

### 3. 配置服务

复制配置模板并编辑：

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml` 文件，根据您的环境配置各项参数：

```yaml
name: obsidian-clip-api-couchdb
version: v1.0.0
description: 网页剪藏 API 服务

# 服务配置
host: 0.0.0.0
port: 8901

# API 鉴权配置
api:
  enabled: true  # 生产环境建议启用
  key: "your-secret-api-key-here"  # 请使用强密码

# CouchDB 配置
couchdb:
  url: "http://admin:your-password@localhost:5984/"
  db_name: "obsidian"  # 数据库名称

# 企业微信配置（可选）
work_wechat:
  corp_id: "your-corp-id"
  agent_id: "your-agent-id"
  corp_secret: "your-corp-secret"
  user_id: ""  # 留空则发送给所有人
  at_all: true

# PicGo 配置（可选）
picgo:
  enabled: true  # 是否启用图床功能
  server: "http://localhost:36677"
  upload_path: "/upload?key=your-secret-key"

# Obsidian 配置
obsidian:
  clippings_path: "Clippings"  # 剪藏文件保存路径

# 调试模式
debug: false  # 生产环境设为 false
```

### 4. 启动服务

使用 Docker Compose 启动：

```bash
docker-compose up -d
```

检查服务状态：

```bash
docker-compose ps
docker-compose logs app
```

## 本地安装

如果您更偏向于本地安装，请按照以下步骤操作。

### 1. 环境准备

#### 安装 Python

确保安装 Python 3.11 或更高版本：

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv

# CentOS/RHEL
sudo yum install python3.11 python3.11-pip

# Windows
# 从 https://python.org 下载安装包

# macOS
brew install python@3.11
```

### 2. 克隆项目

```bash
git clone https://github.com/yourusername/obsidian-clip-api-couchdb.git
cd obsidian-clip-api-couchdb
```

### 3. 创建虚拟环境

```bash
# 创建虚拟环境
python3.11 -m venv venv

# 激活虚拟环境
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 配置服务

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml` 文件（配置内容同 Docker 部署）。

### 6. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8901
```

## 验证安装

### 1. 检查服务状态

访问 `http://localhost:8901` 应该看到服务信息：

```json
{
  "name": "obsidian-clip-api-couchdb",
  "version": "v1.0.0",
  "description": "网页剪藏 API 服务"
}
```

### 2. 测试 API

使用 curl 测试剪藏功能：

```bash
curl -X POST http://localhost:8901/api/clip \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key" \
  -d '{"url": "https://example.com"}'
```

预期响应：

```json
{
  "title": "网页标题",
  "doc_id": "20240306123456_webpage_title"
}
```

## 常见问题

### CouchDB 连接失败

确保：
1. CouchDB 服务正在运行
2. 用户名和密码正确
3. 数据库已创建
4. 网络连接正常

### PicGo 图片上传失败

检查：
1. PicGo 服务是否启动
2. 上传密钥是否正确
3. 图床配置是否有效

### 企业微信通知失败

验证：
1. Corp ID、Agent ID 和 Corp Secret 是否正确
2. 应用是否已发布
3. 网络是否能访问企业微信 API

## 升级指南

### Docker 升级

```bash
# 停止服务
docker-compose down

# 拉取新版本
git pull origin main

# 重新构建并启动
docker-compose up -d --build
```

### 本地升级

```bash
# 激活虚拟环境
source venv/bin/activate

# 更新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade

# 重启服务
uvicorn app.main:app --host 0.0.0.0 --port 8901
```

## 安全建议

1. **更改默认密钥**: 务必修改 API Key 和其他默认密码
2. **启用 HTTPS**: 生产环境建议使用反向代理启用 HTTPS
3. **限制访问**: 使用防火墙限制不必要的网络访问
4. **定期备份**: 定期备份 CouchDB 数据
5. **监控日志**: 定期检查应用日志和系统日志

---

安装完成后，请查看 [快速上手指南](quickstart.md) 了解如何使用服务。
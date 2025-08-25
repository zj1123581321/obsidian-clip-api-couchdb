# 快速上手指南

本指南将帮助您在 5 分钟内完成第一次网页剪藏。假设您已经按照 [安装指南](installation.md) 完成了服务部署。

## 前置条件检查

在开始之前，请确保以下服务已正确运行：

- ✅ Obsidian 剪藏 API 服务（端口 8901）
- ✅ CouchDB 服务（端口 5984）
- ✅ PicGo 服务（可选，端口 36677）
- ✅ 企业微信应用（可选）

## 第一步：验证服务状态

打开浏览器或使用 curl 检查服务是否正常运行：

```bash
curl http://localhost:8901
```

预期响应：
```json
{
  "name": "obsidian-clip-api-couchdb",
  "version": "v1.0.0",
  "description": "网页剪藏 API 服务"
}
```

## 第二步：配置 Obsidian LiveSync

### 1. 安装 Obsidian LiveSync 插件

在 Obsidian 中安装并启用 [obsidian-livesync](https://github.com/vrtmrz/obsidian-livesync) 插件。

### 2. 配置 CouchDB 连接

在 LiveSync 插件设置中配置：

- **Remote Database URI**: `http://admin:your-password@localhost:5984/obsidian`
- **Database Name**: `obsidian`（与配置文件中的 `couchdb.db_name` 一致）
- **Username**: `admin`
- **Password**: `your-password`

### 3. 初始化数据库

点击 "Test Database Connection" 验证连接，然后点击 "Initialize Database" 初始化数据库。

## 第三步：进行第一次剪藏

### 方法一：使用 curl 命令

```bash
curl -X POST http://localhost:8901/api/clip \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key" \
  -d '{"url": "https://example.com/article"}'
```

### 方法二：使用 HTTP 客户端

如果您使用 Postman、Insomnia 或类似工具：

**请求配置：**
- **方法**: POST
- **URL**: `http://localhost:8901/api/clip`
- **Headers**: 
  - `Content-Type: application/json`
  - `X-API-Key: your-secret-api-key`
- **Body** (JSON):
  ```json
  {
    "url": "https://example.com/article"
  }
  ```

### 成功响应示例

```json
{
  "title": "示例文章标题",
  "doc_id": "20240306123456_example_article_title"
}
```

## 第四步：查看剪藏结果

### 在 Obsidian 中查看

1. 打开 Obsidian
2. 触发 LiveSync 同步（插件会自动同步，也可以手动触发）
3. 在 `Clippings` 文件夹中找到新创建的文档

### 文档格式预览

剪藏的文档包含 YAML front matter 和 Markdown 内容：

```markdown
---
url: https://example.com/article
title: 示例文章标题
description: 文章描述信息
author: 作者姓名
published: 2024-03-06
created: 2024-03-06 15:30
---

# 文章标题

文章的正文内容会在这里，格式化为 Markdown...

![图片描述](https://your-image-host.com/image.jpg)

文章的其他内容...
```

## 第五步：配置浏览器插件（推荐）

为了更方便地使用剪藏功能，建议创建浏览器书签或使用用户脚本。

### 创建书签工具

在浏览器中创建以下书签：

**书签名称**: `剪藏到 Obsidian`

**书签地址**:
```javascript
javascript:(function(){
  const currentUrl = window.location.href;
  const apiUrl = 'http://localhost:8901/api/clip';
  const apiKey = 'your-secret-api-key';
  
  fetch(apiUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey
    },
    body: JSON.stringify({url: currentUrl})
  })
  .then(response => response.json())
  .then(data => {
    if (data.title) {
      alert('剪藏成功: ' + data.title);
    } else {
      alert('剪藏失败: ' + (data.error || '未知错误'));
    }
  })
  .catch(error => {
    alert('网络错误: ' + error.message);
  });
})();
```

### 使用书签工具

1. 访问您想要剪藏的网页
2. 点击浏览器书签栏中的 "剪藏到 Obsidian" 书签
3. 等待剪藏完成的提示

## 企业微信通知（可选）

如果您配置了企业微信通知，在剪藏过程中会收到以下消息：

### 开始剪藏通知
```
📥 开始剪藏
时间：2024-03-06 15:30:25
链接：https://example.com/article
图床：已开启
```

### 成功通知
```
✅ 剪藏成功
标题：示例文章标题
链接：https://example.com/article
路径：Clippings/20240306123456_example_article_title.md
```

### 错误通知
```
❌ 剪藏失败
错误：无法访问指定网页
```

## 常见问题解决

### API 密钥错误

如果看到 "无效的 API 密钥" 错误：
1. 检查 `config.yaml` 中的 `api.key` 设置
2. 确保请求头中的 `X-API-Key` 与配置文件一致
3. 如果不需要鉴权，可以设置 `api.enabled: false`

### CouchDB 连接错误

如果看到数据库连接错误：
1. 确保 CouchDB 服务正在运行
2. 检查 `config.yaml` 中的 CouchDB 配置
3. 验证用户名、密码和数据库名称

### Obsidian 中看不到剪藏文档

1. 检查 LiveSync 插件是否正常工作
2. 手动触发同步
3. 检查 Obsidian 的文件夹设置
4. 确认 `clippings_path` 配置正确

### 图片显示问题

如果图片不显示：
1. 检查 PicGo 服务是否正常运行
2. 验证图床配置是否正确
3. 查看调试日志了解上传过程
4. 可以暂时禁用图床功能：`picgo.enabled: false`

## 进阶使用技巧

### 1. 批量剪藏

编写脚本批量处理多个 URL：

```bash
#!/bin/bash
urls=(
  "https://example1.com/article1"
  "https://example2.com/article2"
  "https://example3.com/article3"
)

for url in "${urls[@]}"; do
  curl -X POST http://localhost:8901/api/clip \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your-secret-api-key" \
    -d "{\"url\": \"$url\"}"
  sleep 2  # 避免请求过于频繁
done
```

### 2. 自定义保存路径

通过修改 `config.yaml` 中的 `obsidian.clippings_path` 来自定义保存路径：

```yaml
obsidian:
  clippings_path: "Articles/WebClips"  # 保存到 Articles/WebClips 文件夹
```

### 3. 启用调试模式

在开发或排错时，可以启用调试模式：

```yaml
debug: true  # 会在 debug/ 文件夹生成调试文件
```

---

恭喜！您已经成功完成第一次网页剪藏。接下来可以查看 [架构文档](architecture.md) 了解系统的详细设计，或者查看 [API 文档](api.md) 了解更多高级功能。
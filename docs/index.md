# Obsidian 剪藏 API 文档

欢迎来到 Obsidian 剪藏 API 服务的官方文档。这是一个高效、安全、功能完整的网页剪藏解决方案，专为 Obsidian 用户设计。

## 项目简介

Obsidian 剪藏 API 是一个用于剪藏网页内容到 Obsidian 笔记软件的 REST API 服务。该项目基于 [obcsapi-go](https://github.com/kkbt0/obcsapi-go) 用 Python 重写，提供了更强大的功能和更好的扩展性。

## 核心特性

- **智能内容提取**: 使用先进的网页解析技术，准确提取文章内容和元数据
- **Markdown 转换**: 将网页内容智能转换为高质量的 Markdown 格式
- **图片处理**: 自动提取图片并上传到 PicGo 图床，支持多种图床服务
- **CouchDB 存储**: 与 Obsidian LiveSync 插件无缝集成，实现跨设备同步
- **企业微信通知**: 实时推送剪藏状态，包括开始、成功、失败等状态
- **API 鉴权**: 支持 API Key 验证，确保服务安全
- **Docker 部署**: 一键部署，支持容器化运行
- **调试模式**: 丰富的调试信息，方便问题排查

## 技术架构

本项目采用现代化的 Python 技术栈：

- **Web 框架**: FastAPI - 高性能异步 Web 框架
- **内容解析**: BeautifulSoup4 + trafilatura - 智能网页内容提取
- **数据存储**: CouchDB - 分布式文档数据库
- **图片上传**: PicGo Server 集成 - 支持多种图床服务
- **通知服务**: 企业微信 API - 实时状态推送
- **容器化**: Docker + Docker Compose - 便捷部署

## 快速导航

### 🚀 开始使用
- [安装指南](installation.md) - 详细的安装和配置说明
- [快速上手](quickstart.md) - 5分钟完成第一次剪藏

### 📚 深入了解
- [系统架构](architecture.md) - 了解系统设计和组件关系
- [API 文档](api.md) - 完整的 API 接口说明
- [配置参考](configuration.md) - 详细的配置选项说明

### 🔧 高级使用
- [部署指南](deployment.md) - 生产环境部署最佳实践
- [故障排查](troubleshooting.md) - 常见问题和解决方案
- [开发指南](development.md) - 二次开发和贡献指南

## 使用场景

- **知识管理**: 将有价值的网络文章收集到 Obsidian 知识库
- **学术研究**: 收集研究资料并自动生成引用信息
- **团队协作**: 通过企业微信通知团队成员剪藏结果
- **内容归档**: 建立个人或组织的内容归档系统

## 项目状态

- **版本**: v1.0.0
- **许可证**: MIT
- **维护状态**: 积极维护
- **Python 版本**: 3.11+
- **Docker 支持**: ✅

## 社区与支持

- **问题反馈**: 通过 GitHub Issues 报告问题
- **功能建议**: 欢迎提交 Feature Request
- **贡献代码**: 查看 [开发指南](development.md)

---

开始您的 Obsidian 剪藏之旅，让知识管理变得更加高效！